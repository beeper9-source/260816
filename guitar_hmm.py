import math

# Standard guitar tuning: string 1 is high E, string 6 is low E.
# Values are MIDI numbers.
TUNING = {
    1: 64,  # E4
    2: 59,  # B3
    3: 55,  # G3
    4: 50,  # D3
    5: 45,  # A2
    6: 40   # E2
}

class NoteState:
    def __init__(self, string, fret, finger, position=None):
        self.string = string     # 1 to 6
        self.fret = fret         # 0 to 19
        self.finger = finger     # 0 (open), 1 (index), 2 (middle), 3 (ring), 4 (little)
        
        if fret > 0 and position is None:
            self.position = max(1, fret - finger + 1)
        else:
            self.position = position if position is not None else 1

    def __repr__(self):
        return f"S{self.string}F{self.fret}f{self.finger}p{self.position}"

    def __eq__(self, other):
        if not isinstance(other, NoteState):
            return False
        return (self.string == other.string and 
                self.fret == other.fret and 
                self.finger == other.finger and
                self.position == other.position)

    def __hash__(self):
        return hash((self.string, self.fret, self.finger, self.position))


class ChordState:
    def __init__(self, note_states, position):
        # Sort by string number to have a deterministic representation
        self.note_states = sorted(note_states, key=lambda ns: ns.string)
        self.position = position

    def __repr__(self):
        if not self.note_states:
            return f"[Rest]p{self.position}"
        return "[" + ",".join(repr(ns) for ns in self.note_states) + f"]p{self.position}"

    def __eq__(self, other):
        if not isinstance(other, ChordState):
            return False
        return self.note_states == other.note_states and self.position == other.position

    def __hash__(self):
        return hash((tuple(self.note_states), self.position))


def get_possible_note_states(pitch):
    """Find all possible string, fret, finger combinations for a pitch."""
    states = []
    for string, open_pitch in TUNING.items():
        fret = pitch - open_pitch
        if 0 <= fret <= 19:
            if fret == 0:
                # Return placeholder note state with position=None
                states.append(NoteState(string, 0, 0, None))
            else:
                for finger in [1, 2, 3, 4]:
                    states.append(NoteState(string, fret, finger))
    return states


def is_valid_chord_combination(note_states):
    """Check if a set of NoteStates is physically playable as a chord."""
    if not note_states:
        return True

    # 1. No duplicate strings
    strings = [ns.string for ns in note_states]
    if len(strings) != len(set(strings)):
        return False

    # Filter fretted notes
    fretted = [ns for ns in note_states if ns.fret > 0]
    
    # 2. Check finger assignments
    if any(ns.finger == 0 for ns in fretted):
        return False

    finger_counts = {}
    for ns in fretted:
        finger_counts[ns.finger] = finger_counts.get(ns.finger, 0) + 1

    # Finger 1 barre check: if finger 1 is used multiple times, it must be on the same fret
    f1_notes = [ns for ns in fretted if ns.finger == 1]
    if len(f1_notes) > 1:
        barre_fret = f1_notes[0].fret
        if any(ns.fret != barre_fret for ns in f1_notes):
            return False

    # Other fingers (2, 3, 4) must be used at most once
    for f_idx in [2, 3, 4]:
        if finger_counts.get(f_idx, 0) > 1:
            return False

    # 3. Fret stretch constraint
    if fretted:
        frets = [ns.fret for ns in fretted]
        max_f = max(frets)
        min_f = min(frets)
        if max_f - min_f > 4:
            return False

    # 4. Finger order vs fret order constraint (avoid crossed fingers)
    for i in range(len(fretted)):
        for j in range(i + 1, len(fretted)):
            ns_a = fretted[i]
            ns_b = fretted[j]
            if ns_a.finger == ns_b.finger:
                continue
            if ns_a.finger < ns_b.finger:
                fi_1, f_1 = ns_a.finger, ns_a.fret
                fi_2, f_2 = ns_b.finger, ns_b.fret
            else:
                fi_1, f_1 = ns_b.finger, ns_b.fret
                fi_2, f_2 = ns_a.finger, ns_a.fret
            
            # Constraint: f_2 should not be significantly lower than f_1
            max_allowed_lower = fi_2 - fi_1 - 1
            if f_2 < f_1 - max_allowed_lower:
                return False

    return True


def get_possible_chord_states(pitches):
    """Generate all valid ChordStates for a given list of pitches."""
    if not pitches:
        # Rest state: can carry over hand position in any position 1 to 15
        return [ChordState([], pos) for pos in range(1, 16)]

    unique_pitches = list(set(pitches))
    candidates_per_pitch = [get_possible_note_states(p) for p in unique_pitches]
    if any(not c for c in candidates_per_pitch):
        return []

    valid_chords = []

    def search(pitch_idx, current_states):
        if pitch_idx == len(unique_pitches):
            # Find hand position of the fretted notes
            fretted_positions = [ns.position for ns in current_states if ns.fret > 0]
            if fretted_positions:
                min_pos = min(fretted_positions)
                max_pos = max(fretted_positions)
                if max_pos - min_pos > 1:
                    # Allow suggested positions to differ by at most 1 fret
                    return
                pos = min_pos
            else:
                pos = None

            if is_valid_chord_combination(current_states):
                if pos is not None:
                    # Update all notes in the chord to have the same position
                    final_states = []
                    for ns in current_states:
                        if ns.fret == 0:
                            final_states.append(NoteState(ns.string, 0, 0, pos))
                        else:
                            final_states.append(NoteState(ns.string, ns.fret, ns.finger, pos))
                    valid_chords.append(ChordState(final_states, pos))
                else:
                    # Only open strings: generate for all possible positions 1 to 15
                    for p_val in range(1, 16):
                        final_states = [NoteState(ns.string, 0, 0, p_val) for ns in current_states]
                        valid_chords.append(ChordState(final_states, p_val))
            return
        
        for ns in candidates_per_pitch[pitch_idx]:
            if any(ns.string == existing.string for existing in current_states):
                continue
            search(pitch_idx + 1, current_states + [ns])

    search(0, [])
    return valid_chords


def calculate_state_cost(state):
    """Compute the static difficulty cost of a chord state."""
    cost = 0.0
    
    # 1. Prefer lower frets (closer to first position)
    for ns in state.note_states:
        if ns.fret > 0:
            cost += 0.1 * ns.fret
            if ns.fret > 12:
                cost += 0.2 * (ns.fret - 12)
        else:
            # Open string bonus (makes it preferred)
            cost -= 0.15

    # 2. Barre penalty (barres are slightly harder)
    f1_notes = [ns for ns in state.note_states if ns.finger == 1 and ns.fret > 0]
    if len(f1_notes) > 1:
        cost += 0.8  # slight penalty for holding a barre

    # 3. Chord thickness penalty (playing more notes simultaneously is harder)
    if len(state.note_states) > 1:
        cost += 0.4 * len(state.note_states)

    # 4. Position penalty (strongly prefer lower positions, especially first position)
    cost += 0.05 * (state.position - 1)

    # 5. Hand comfort / posture penalties
    fretted = [ns for ns in state.note_states if ns.fret > 0]
    for i in range(len(fretted)):
        for j in range(i + 1, len(fretted)):
            ns_a = fretted[i]
            ns_b = fretted[j]
            
            # (a) Backward stretch penalty (higher finger on lower fret)
            if ns_a.finger < ns_b.finger and ns_a.fret > ns_b.fret:
                cost += 0.5
            elif ns_b.finger < ns_a.finger and ns_b.fret > ns_a.fret:
                cost += 0.5
                
            # (b) Vertical crossing penalty (higher finger on lower-pitched string for same fret)
            if ns_a.fret == ns_b.fret:
                if ns_a.string > ns_b.string and ns_a.finger > ns_b.finger:
                    cost += 0.5
                elif ns_b.string > ns_a.string and ns_b.finger > ns_a.finger:
                    cost += 0.5

    return cost


def calculate_transition_cost(s1, s2):
    """Compute the transition difficulty cost from state s1 to state s2."""
    cost = 0.0

    # 1. Hand position shift cost (now always defined!)
    shift = abs(s1.position - s2.position)
    if shift > 0:
        # Shift penalty: non-linear cost.
        if shift <= 2:
            cost += 1.0 * shift
        else:
            cost += 2.0 + 3.0 * (shift - 2)

    # If either state is a rest, only shift cost applies
    if not s1.note_states or not s2.note_states:
        return cost

    # 2. Finger continuity and movements
    f_map1 = {ns.finger: ns for ns in s1.note_states if ns.finger > 0}
    f_map2 = {ns.finger: ns for ns in s2.note_states if ns.finger > 0}

    for finger in [1, 2, 3, 4]:
        ns1 = f_map1.get(finger)
        ns2 = f_map2.get(finger)
        
        if ns1 and ns2:
            # Same finger used in both states
            if ns1.fret == ns2.fret and ns1.string == ns2.string:
                continue
            elif ns1.fret == ns2.fret and ns1.string != ns2.string:
                if finger == 1:
                    cost += 1.2
                else:
                    cost += 3.5
            else:
                fret_diff = abs(ns1.fret - ns2.fret)
                if ns1.string == ns2.string:
                    cost += 1.5 + 0.5 * fret_diff
                else:
                    cost += 7.0 + 1.0 * fret_diff

    # 3. String crossing cost (for single-note melodic sequences)
    if len(s1.note_states) == 1 and len(s2.note_states) == 1:
        ns1 = s1.note_states[0]
        ns2 = s2.note_states[0]
        string_diff = abs(ns1.string - ns2.string)
        if string_diff > 1:
            cost += 0.25 * string_diff

    return cost


def solve_fingering(note_sequence):
    """
    Find the optimal sequence of ChordStates for a given sequence of note events.
    note_sequence: list of lists, where each inner list contains MIDI pitches representing a chord/note event.
    """
    if not note_sequence:
        return []

    # Generate all candidate states for each event
    stages = []
    for pitches in note_sequence:
        candidates = get_possible_chord_states(pitches)
        if not candidates:
            # Fallback: find playable subset of pitches
            playable_pitches = [p for p in pitches if any(p - op >= 0 and p - op <= 19 for op in TUNING.values())]
            candidates = get_possible_chord_states(playable_pitches)
            if not candidates:
                candidates = [ChordState([], pos) for pos in range(1, 16)]
        stages.append(candidates)

    n = len(stages)
    # dp[t][state] = min cost to reach state at stage t
    dp = [{} for _ in range(n)]
    parent = [{} for _ in range(n)]

    # Initialize stage 0
    for state in stages[0]:
        dp[0][state] = calculate_state_cost(state)

    # Dynamic programming forward pass
    for t in range(1, n):
        for curr_state in stages[t]:
            min_cost = float('inf')
            best_prev = None
            
            for prev_state in dp[t-1]:
                trans_cost = calculate_transition_cost(prev_state, curr_state)
                total_cost = dp[t-1][prev_state] + trans_cost
                
                if total_cost < min_cost:
                    min_cost = total_cost
                    best_prev = prev_state
            
            dp[t][curr_state] = min_cost + calculate_state_cost(curr_state)
            parent[t][curr_state] = best_prev

    # Find the best final state
    min_final_cost = float('inf')
    best_final_state = None
    for state in dp[n-1]:
        if dp[n-1][state] < min_final_cost:
            min_final_cost = dp[n-1][state]
            best_final_state = state

    if best_final_state is None:
        return []

    # Backtrack to find the optimal path
    path = [None] * n
    curr = best_final_state
    for t in range(n-1, -1, -1):
        path[t] = curr
        curr = parent[t][curr] if t > 0 else None

    return path
