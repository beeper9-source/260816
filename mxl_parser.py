import os
import xml.etree.ElementTree as ET
import zipfile
import tempfile
from music21 import converter
from guitar_hmm import solve_fingering, TUNING

def get_default_string(pitch):
    """
    Get the default guitar string (1 to 6) for a given MIDI pitch in standard first position.
    """
    if pitch <= 44:       # E2 to G#2
        return 6
    elif 45 <= pitch <= 49: # A2 to C#3
        return 5
    elif 50 <= pitch <= 54: # D3 to F#3
        return 4
    elif 55 <= pitch <= 58: # G3 to A#3
        return 3
    elif 59 <= pitch <= 63: # B3 to D#4
        return 2
    else:                  # E4 and above
        return 1

def determine_transposition(part):
    # Extract all music21 pitches (without transposition)
    pitches = []
    for el in part.flatten().notes:
        if el.isChord:
            pitches.extend([int(round(p.ps)) for p in el.pitches])
        else:
            pitches.append(int(round(el.pitch.ps)))
    if not pitches:
        return 0
    min_pitch = min(pitches)
    # If the lowest pitch is already below 38, it must be sounding pitch
    if min_pitch < 38:
        return 0
    # Check how many notes would become unplayable (below 38) if we transposed by -12
    unplayable_count = sum(1 for p in pitches if p - 12 < 38)
    if unplayable_count > 0:
        return 0
    else:
        return -12

def extract_note_sequence(score_or_part):
    """
    Extract the sequence of pitches (grouped by onset offset).
    Can take a music21 Score or Part.
    """
    if hasattr(score_or_part, 'parts'):
        # If it's a Score, use the first part
        parts = list(score_or_part.parts)
        if not parts:
            raise ValueError("The MusicXML file does not contain any parts.")
        part = parts[0]
    else:
        part = score_or_part
        
    notes_and_chords = list(part.flatten().notes)
    
    # Group notes/chords by offset
    events = {}
    for el in notes_and_chords:
        # Ignore rests and grace notes for simple alignment
        if el.isRest or getattr(el, 'duration', None) is None or el.duration.quarterLength == 0:
            continue
        offset = el.offset
        if offset not in events:
            events[offset] = []
        events[offset].append(el)
        
    sorted_offsets = sorted(events.keys())
    
    # Determine transposition dynamically
    transpose = determine_transposition(part)
    
    note_sequence = []
    offset_to_pitches = {}
    
    for offset in sorted_offsets:
        pitches = []
        for el in events[offset]:
            if el.isChord:
                pitches.extend([int(round(p.ps)) + transpose for p in el.pitches])
            else:
                pitches.append(int(round(el.pitch.ps)) + transpose)
        note_sequence.append(pitches)
        offset_to_pitches[offset] = pitches
        
    return note_sequence, sorted_offsets, transpose

def annotate_single_part_element(part_el, optimal_path, offsets, transpose=-12):
    """
    Track timeline, align and annotate notes within a single XML part element.
    """
    # 1. Track timeline of all notes in this XML part
    current_time = 0  # in divisions
    divisions = 1
    xml_notes_with_times = []  # list of (note_element, start_time_quarters, midi_pitch)
    
    for measure in part_el.findall('measure'):
        attr = measure.find('attributes')
        if attr is not None:
            div_el = attr.find('divisions')
            if div_el is not None:
                divisions = int(div_el.text)
        
        note_start_time = current_time
        
        for child in measure:
            if child.tag == 'note':
                is_grace = child.find('grace') is not None
                is_chord = child.find('chord') is not None
                is_rest = child.find('rest') is not None
                
                dur_el = child.find('duration')
                duration = int(dur_el.text) if dur_el is not None else 0
                
                if is_chord:
                    start_time = note_start_time
                else:
                    start_time = current_time
                    note_start_time = current_time
                
                if not is_rest and not is_grace:
                    pitch_el = child.find('pitch')
                    if pitch_el is not None:
                        step = pitch_el.find('step').text
                        alter_el = pitch_el.find('alter')
                        alter = int(alter_el.text) if alter_el is not None else 0
                        octave = int(pitch_el.find('octave').text)
                        
                        # Get written MIDI pitch from XML
                        midi_pitch = 12 * (octave + 1) + {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[step] + alter
                        
                        start_time_quarters = start_time / divisions
                        xml_notes_with_times.append((child, start_time_quarters, midi_pitch))
                
                if not is_chord and not is_grace:
                    current_time += duration
                    
            elif child.tag == 'backup':
                dur_el = child.find('duration')
                duration = int(dur_el.text) if dur_el is not None else 0
                current_time -= duration
                
            elif child.tag == 'forward':
                dur_el = child.find('duration')
                duration = int(dur_el.text) if dur_el is not None else 0
                current_time += duration

    # 2. Align and annotate notes
    offset_to_index = {offset: idx for idx, offset in enumerate(offsets)}
    assigned_states_per_step = {idx: set() for idx in range(len(optimal_path))}
    
    annotated_count = 0
    for note_el, start_time, midi_pitch in xml_notes_with_times:
        matched_idx = None
        for offset in offsets:
            if abs(offset - start_time) < 1e-2:
                matched_idx = offset_to_index[offset]
                break
        
        if matched_idx is not None:
            chord_state = optimal_path[matched_idx]
            xml_sounding_pitch = midi_pitch + transpose
            
            # Find matching note state
            matched_ns = None
            # Pass 1: Try to find an unassigned note state
            for ns in chord_state.note_states:
                ns_pitch = TUNING[ns.string] + ns.fret
                if ns_pitch == xml_sounding_pitch and ns not in assigned_states_per_step[matched_idx]:
                    matched_ns = ns
                    assigned_states_per_step[matched_idx].add(ns)
                    break
            
            # Pass 2: Fallback to duplicate matching if no unassigned note state of the same pitch is found
            if matched_ns is None:
                for ns in chord_state.note_states:
                    ns_pitch = TUNING[ns.string] + ns.fret
                    if ns_pitch == xml_sounding_pitch:
                        matched_ns = ns
                        break
            
            if matched_ns:
                # Check if the entire chord state is repeated from the previous step
                is_chord_repeated = False
                if matched_idx > 0:
                    prev_state = optimal_path[matched_idx - 1]
                    curr_state = optimal_path[matched_idx]
                    if prev_state == curr_state:
                        is_chord_repeated = True

                notations = note_el.find('notations')
                if notations is None:
                    notations = ET.Element('notations')
                    note_el.append(notations)
                    
                technical = notations.find('technical')
                if technical is None:
                    technical = ET.Element('technical')
                    notations.append(technical)
                
                for child in list(technical):
                    if child.tag in ['fingering', 'string']:
                        technical.remove(child)
                
                # Determine if string number is needed (omit if default/obvious or repeated)
                need_string = False
                if matched_ns.string > 0 and matched_ns.fret > 0 and not is_chord_repeated:
                    default_str = get_default_string(midi_pitch)
                    if matched_ns.string != default_str:
                        need_string = True
                
                if need_string:
                    str_el = ET.Element('string')
                    str_el.text = str(matched_ns.string)
                    technical.append(str_el)
                
                # Always print the fingering
                f_el = ET.Element('fingering')
                f_el.text = str(matched_ns.finger)
                technical.append(f_el)
                
                annotated_count += 1
                
    return annotated_count, len(xml_notes_with_times)

def annotate_xml_content(xml_string, part_results_or_path, offsets=None):
    """
    Parse XML content and inject fingering and string annotations.
    Supports:
      - annotate_xml_content(xml_string, part_results)
      - annotate_xml_content(xml_string, optimal_path, offsets) [backward compatibility]
    """
    if offsets is not None:
        part_results = [('P1', part_results_or_path, offsets)]
    else:
        part_results = part_results_or_path
        
    root = ET.fromstring(xml_string)
    
    xml_parts = root.findall('.//part')
    if not xml_parts:
        return xml_string, 0, 0
    
    results_by_id = {}
    for item in part_results:
        if len(item) == 4:
            pid, path, offsets, transpose = item
            results_by_id[pid] = (path, offsets, transpose)
        else:
            pid, path, offsets = item
            results_by_id[pid] = (path, offsets, -12)
            
    total_annotated = 0
    total_notes = 0
    
    for idx, part_el in enumerate(xml_parts):
        part_id = part_el.get('id')
        matched_result = results_by_id.get(part_id)
        if matched_result is None and idx < len(part_results):
            r = part_results[idx]
            if len(r) == 4:
                matched_result = (r[1], r[2], r[3])
            else:
                matched_result = (r[1], r[2], -12)
            
        if matched_result:
            optimal_path, offsets, transpose = matched_result
            print(f"[XML Parser] Annotating part {part_id if part_id else idx+1}...")
            annotated_count, part_note_count = annotate_single_part_element(part_el, optimal_path, offsets, transpose)
            print(f"[XML Parser] Part {part_id if part_id else idx+1}: annotated {annotated_count} / {part_note_count} notes.")
            total_annotated += annotated_count
            total_notes += part_note_count
            
    print(f"[XML Parser] Successfully annotated {total_annotated} / {total_notes} notes total.")
    
    annotated_xml = ET.tostring(root, encoding='utf-8')
    xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + annotated_xml
    return xml_bytes, total_annotated, total_notes

def create_mxl_file(xml_content, output_path):
    """
    Zip XML content into a valid compressed MusicXML (.mxl) file.
    """
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
           xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="score.musicxml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>"""
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('META-INF/container.xml', container_xml)
        zipf.writestr('score.musicxml', xml_content)

def annotate_mxl(input_path, output_path):
    """
    Main function to parse an MXL/MusicXML file, calculate guitar fingerings, 
    and output the annotated score.
    """
    print(f"[MXL Parser] Loading file: {input_path}")
    score = converter.parse(input_path)
    
    parts = list(score.parts)
    print(f"[MXL Parser] Number of parts detected: {len(parts)}")
    
    part_results = []
    for idx, part in enumerate(parts):
        print(f"[MXL Parser] Processing Part {idx+1} (ID: {part.id})...")
        note_sequence, offsets, transpose = extract_note_sequence(part)
        print(f"[MXL Parser] Solving guitar fingerings using HMM (length={len(note_sequence)})...")
        optimal_path = solve_fingering(note_sequence)
        part_results.append((part.id, optimal_path, offsets, transpose))
    
    # Export the score to temporary MusicXML
    print("[MXL Parser] Exporting temporary score...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_xml_path = os.path.join(temp_dir, "temp.musicxml")
        score.write('musicxml', fp=temp_xml_path)
        
        # Read the raw XML content
        with open(temp_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        print("[MXL Parser] Injecting fingering and string annotations into XML...")
        annotated_xml_content, annotated, total = annotate_xml_content(xml_content, part_results)
        
        # Write output file
        if output_path.lower().endswith('.mxl'):
            print(f"[MXL Parser] Compressing output to MXL: {output_path}")
            create_mxl_file(annotated_xml_content, output_path)
        else:
            print(f"[MXL Parser] Writing output to MusicXML: {output_path}")
            with open(output_path, 'wb') as f_out:
                f_out.write(annotated_xml_content)
                
    print("[MXL Parser] Done successfully!")
    return annotated, total
