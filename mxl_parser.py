import os
import xml.etree.ElementTree as ET
import zipfile
import tempfile
from music21 import converter
from guitar_hmm import solve_fingering, TUNING

def extract_note_sequence(score):
    """
    Extract the sequence of pitches (grouped by onset offset) from the first part of the score.
    """
    # Use the first part of the score
    parts = list(score.parts)
    if not parts:
        raise ValueError("The MusicXML file does not contain any parts.")
    
    part = parts[0]
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
    
    note_sequence = []
    offset_to_pitches = {}
    
    for offset in sorted_offsets:
        pitches = []
        for el in events[offset]:
            if el.isChord:
                pitches.extend([int(round(p.ps)) for p in el.pitches])
            else:
                pitches.append(int(round(el.pitch.ps)))
        note_sequence.append(pitches)
        offset_to_pitches[offset] = pitches
        
    return note_sequence, sorted_offsets

def annotate_xml_content(xml_string, optimal_path, offsets):
    """
    Parse XML content and inject fingering and string annotations by tracking the timeline.
    """
    root = ET.fromstring(xml_string)
    
    parts = root.findall('.//part')
    if not parts:
        return xml_string
    
    part = parts[0]
    
    # 1. Track timeline of all notes in the MusicXML
    current_time = 0  # in divisions
    divisions = 1
    xml_notes_with_times = []  # list of (note_element, start_time_quarters, midi_pitch)
    
    for measure in part.findall('measure'):
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

    print(f"[XML Parser] XML note elements detected: {len(xml_notes_with_times)}")
    print(f"[XML Parser] HMM optimal path steps: {len(optimal_path)}")
    
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
            
            matched_ns = None
            for ns in chord_state.note_states:
                ns_pitch = TUNING[ns.string] + ns.fret
                if ns_pitch == midi_pitch and ns not in assigned_states_per_step[matched_idx]:
                    matched_ns = ns
                    assigned_states_per_step[matched_idx].add(ns)
                    break
            
            if matched_ns:
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
                
                if matched_ns.string > 0:
                    str_el = ET.Element('string')
                    str_el.text = str(matched_ns.string)
                    technical.append(str_el)
                
                if matched_ns.finger > 0:
                    f_el = ET.Element('fingering')
                    f_el.text = str(matched_ns.finger)
                    technical.append(f_el)
                
                annotated_count += 1

    print(f"[XML Parser] Successfully annotated {annotated_count} / {len(xml_notes_with_times)} notes.")
    
    annotated_xml = ET.tostring(root, encoding='utf-8')
    xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + annotated_xml
    return xml_bytes, annotated_count, len(xml_notes_with_times)

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
    
    print("[MXL Parser] Extracting note sequence...")
    note_sequence, offsets = extract_note_sequence(score)
    
    print(f"[MXL Parser] Solving guitar fingerings using HMM (length={len(note_sequence)})...")
    optimal_path = solve_fingering(note_sequence)
    
    # Export the score to temporary MusicXML
    print("[MXL Parser] Exporting temporary score...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_xml_path = os.path.join(temp_dir, "temp.musicxml")
        score.write('musicxml', fp=temp_xml_path)
        
        # Read the raw XML content
        with open(temp_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        print("[MXL Parser] Injecting fingering and string annotations into XML...")
        annotated_xml_content, annotated, total = annotate_xml_content(xml_content, optimal_path, offsets)
        
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
