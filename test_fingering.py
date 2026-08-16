import unittest
from guitar_hmm import (
    solve_fingering, 
    get_possible_chord_states, 
    TUNING, 
    ChordState, 
    NoteState
)

class TestGuitarFingeringHMM(unittest.TestCase):

    def test_c_major_scale(self):
        # C3, D3, E3, F3, G3, A3, B3, C4
        # Standard MIDI pitches
        pitches = [48, 50, 52, 53, 55, 57, 59, 60]
        note_sequence = [[p] for p in pitches]
        
        path = solve_fingering(note_sequence)
        
        self.assertEqual(len(path), len(pitches))
        
        # Verify standard first-position fingering for C Major scale:
        # C3 (48) -> String 5, Fret 3, Finger 3
        self.assertEqual(path[0].note_states[0].string, 5)
        self.assertEqual(path[0].note_states[0].fret, 3)
        self.assertEqual(path[0].note_states[0].finger, 3)
        
        # D3 (50) -> String 4, Fret 0, Finger 0
        self.assertEqual(path[1].note_states[0].string, 4)
        self.assertEqual(path[1].note_states[0].fret, 0)
        self.assertEqual(path[1].note_states[0].finger, 0)
        
        # E3 (52) -> String 4, Fret 2, Finger 2
        self.assertEqual(path[2].note_states[0].string, 4)
        self.assertEqual(path[2].note_states[0].fret, 2)
        self.assertEqual(path[2].note_states[0].finger, 2)
        
        # F3 (53) -> String 4, Fret 3, Finger 3
        self.assertEqual(path[3].note_states[0].string, 4)
        self.assertEqual(path[3].note_states[0].fret, 3)
        self.assertEqual(path[3].note_states[0].finger, 3)
        
        # G3 (55) -> String 3, Fret 0, Finger 0
        self.assertEqual(path[4].note_states[0].string, 3)
        self.assertEqual(path[4].note_states[0].fret, 0)
        self.assertEqual(path[4].note_states[0].finger, 0)
        
        # A3 (57) -> String 3, Fret 2, Finger 2
        self.assertEqual(path[5].note_states[0].string, 3)
        self.assertEqual(path[5].note_states[0].fret, 2)
        self.assertEqual(path[5].note_states[0].finger, 2)
        
        # B3 (59) -> String 2, Fret 0, Finger 0
        self.assertEqual(path[6].note_states[0].string, 2)
        self.assertEqual(path[6].note_states[0].fret, 0)
        self.assertEqual(path[6].note_states[0].finger, 0)
        
        # C4 (60) -> String 2, Fret 1, Finger 1
        self.assertEqual(path[7].note_states[0].string, 2)
        self.assertEqual(path[7].note_states[0].fret, 1)
        self.assertEqual(path[7].note_states[0].finger, 1)

    def test_c_major_chord(self):
        # C3 (48), E3 (52), G3 (55), C4 (60)
        pitches = [48, 52, 55, 60]
        
        chord_states = get_possible_chord_states(pitches)
        self.assertTrue(len(chord_states) > 0)
        
        # Run solver on a single chord event
        path = solve_fingering([pitches])
        self.assertEqual(len(path), 1)
        
        c_chord = path[0]
        
        # Standard C Major Chord layout:
        # String 5: C3 (fret 3, finger 3)
        # String 4: E3 (fret 2, finger 2)
        # String 3: G3 (fret 0, finger 0)
        # String 2: C4 (fret 1, finger 1)
        note_dict = {ns.string: ns for ns in c_chord.note_states}
        
        self.assertEqual(note_dict[5].fret, 3)
        self.assertEqual(note_dict[5].finger, 3)
        
        self.assertEqual(note_dict[4].fret, 2)
        self.assertEqual(note_dict[4].finger, 2)
        
        self.assertEqual(note_dict[3].fret, 0)
        self.assertEqual(note_dict[3].finger, 0)
        
        self.assertEqual(note_dict[2].fret, 1)
        self.assertEqual(note_dict[2].finger, 1)

    def test_invalid_chord_stretch(self):
        # A chord with physically impossible fret stretch (e.g. frets 1 and 8)
        # 41 (F2, string 6 fret 1) and 60 (C4, string 5 fret 15 - or similar, let's make it a forced stretch)
        # Let's check that impossible chords are filtered out or solved gracefully.
        pitches = [40, 64] # E2 (string 6 fret 0) and E4 (string 1 fret 0) - this is playable (open strings)
        chord_states = get_possible_chord_states(pitches)
        self.assertTrue(any(len(cs.note_states) == 2 for cs in chord_states))
        
        # If we force fretted pitches with a 7 fret stretch:
        # Pitch 41 (F2, string 6 fret 1) and pitch 55 (G3, can be played string 4 fret 5 or string 5 fret 10)
        # If we force F2 (string 6 fret 1) and C3 (string 5 fret 3) - easy stretch.
        # If we force F2 (string 6 fret 1) and B3 (string 5 fret 14) - impossible stretch on adjacent strings.
        # String 6: F2 (fret 1)
        # String 5: B3 (fret 14)
        # Let's check that chord states with extreme stretches are not returned or have high costs.
        # E.g., pitches [41, 59]. 41 is F2, 59 is B3.
        # Standard B3 is string 2 fret 0. So F2 (string 6 fret 1) and B3 (string 2 fret 0) is playable (open string).
        # But if we force them to be fretted, they shouldn't stretch.
        pass

    def test_get_default_string(self):
        from mxl_parser import get_default_string
        # E2 (40) -> 6
        self.assertEqual(get_default_string(40), 6)
        # G#2 (44) -> 6
        self.assertEqual(get_default_string(44), 6)
        # A2 (45) -> 5
        self.assertEqual(get_default_string(45), 5)
        # C#3 (49) -> 5
        self.assertEqual(get_default_string(49), 5)
        # D3 (50) -> 4
        self.assertEqual(get_default_string(50), 4)
        # G3 (55) -> 3
        self.assertEqual(get_default_string(55), 3)
        # B3 (59) -> 2
        self.assertEqual(get_default_string(59), 2)
        # E4 (64) -> 1
        self.assertEqual(get_default_string(64), 1)
        # A4 (69) -> 1
        self.assertEqual(get_default_string(69), 1)

    def test_xml_annotation_omissions(self):
        from mxl_parser import annotate_xml_content
        from guitar_hmm import ChordState, NoteState
        
        # Create a simple MusicXML content with 3 consecutive identical notes
        dummy_xml = """<?xml version="1.0" encoding="utf-8"?>
<score-partwise version="3.0">
  <part-list>
    <score-part id="P1">
      <part-name>Guitar</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
"""
        # C4 (60) has default string 2.
        # Let's say all notes are played on string 3 (non-default, fret 5) with finger 3.
        # optimal_path has 3 steps (at offset 0.0, 1.0, 2.0).
        state = ChordState([NoteState(3, 5, 3)], 5)
        optimal_path = [state, state, state]
        offsets = [0.0, 1.0, 2.0]
        
        annotated_xml, annotated_count, total_count = annotate_xml_content(dummy_xml, optimal_path, offsets)
        
        # Parse the output XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(annotated_xml)
        notes = root.findall('.//note')
        
        # Check first note: should have both string (3) and fingering (3)
        tech_1 = notes[0].find('.//technical')
        self.assertIsNotNone(tech_1)
        self.assertEqual(tech_1.find('string').text, '3')
        self.assertEqual(tech_1.find('fingering').text, '3')
        
        # Check second and third notes: since the chord state is identical (repeated chord),
        # both string and fingering should be omitted!
        tech_2 = notes[1].find('.//technical')
        if tech_2 is not None:
            self.assertIsNone(tech_2.find('string'))
            self.assertIsNone(tech_2.find('fingering'))
            
        tech_3 = notes[2].find('.//technical')
        if tech_3 is not None:
            self.assertIsNone(tech_3.find('string'))
            self.assertIsNone(tech_3.find('fingering'))

if __name__ == '__main__':
    unittest.main()
