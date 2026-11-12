from recognition.vocabulary import QUESTION, TWO_VALUES, Place, Value, compile_map, read, tokens

NORTH = Place("p-north", ("Acceso Norte",))
BRIDGE = Place("p-bridge", ("Puente", "el puente viejo"))
GATE_17 = Place("p-17", ("Portón 17",))
GATE_170 = Place("p-170", ("Portón 170",))
OPEN = Value("v-open", "k-status", ("abierto", "habilitado", "✅", "سالك"))
CLOSED = Value("v-closed", "k-status", ("cerrado", "cortado", "🔴", "مسكر"))
CHECKS = Value("v-checks", "k-control", ("control", "تفتيش"))
BOTH_WAYS = Value("v-both", "k-direction", ("en los dos sentidos",))

READER = compile_map([NORTH, BRIDGE, GATE_17, GATE_170], [OPEN, CLOSED, CHECKS, BOTH_WAYS])


def _said(text, **kwargs):
    return [(found.line, found.point_id, found.value_id, found.doubt) for found in read(READER, text, **kwargs)]


def test_a_line_that_names_a_place_and_says_a_value_suggests_them():
    assert _said("Acceso Norte cerrado") == [(0, "p-north", "v-closed", None)]
    assert read(READER, "Acceso Norte cerrado")[0].words == ("Acceso Norte", "cerrado")


def test_a_bulletin_gives_a_suggestion_per_line():
    bulletin = "Buen día, así están los pasos:\nAcceso Norte habilitado\n\nPuente cortado\nPortón 17 ✅"
    assert _said(bulletin) == [
        (1, "p-north", "v-open", None),
        (3, "p-bridge", "v-closed", None),
        (4, "p-17", "v-open", None),
    ]


def test_a_line_can_say_values_of_more_than_one_key_of_a_place():
    assert {s[2] for s in _said("Puente cerrado y control en los dos sentidos")} == {"v-closed", "v-checks", "v-both"}


def test_a_word_is_a_whole_word_and_a_number_is_the_whole_number():
    assert _said("Portón 170 abierto") == [(0, "p-170", "v-open", None)]
    assert _said("Portón 17 abierto") == [(0, "p-17", "v-open", None)]
    # "controles" says "control" (another ending of its language), but "descontrol" does not
    assert _said("Puente controles") == [(0, "p-bridge", "v-checks", None)]
    assert _said("Puente descontrol") == []


def test_a_name_of_more_than_one_word_takes_the_longest():
    assert read(READER, "el puente viejo cerrado")[0].words == ("el puente viejo", "cerrado")


def test_arabic_words_match_with_a_prefix_stuck_to_them_and_longer_endings():
    sindyan = Place("p-s", ("السنديان",))
    reader = compile_map([sindyan], [OPEN, CLOSED, CHECKS])
    found = read(reader, "🔴 السنديان مسكرين وتفتيش")
    assert {(s.point_id, s.value_id) for s in found} == {("p-s", "v-closed"), ("p-s", "v-checks")}
    assert {s.value_id for s in read(reader, "بالسنديان سالكات")} == {"v-open"}


def test_what_a_line_says_goes_to_the_place_nearest_to_it():
    assert _said("Acceso Norte cerrado, Puente abierto") == [
        (0, "p-north", "v-closed", None), (0, "p-bridge", "v-open", None),
    ]


def test_a_line_without_a_place_speaks_of_the_place_of_its_group_when_it_has_one():
    assert _said("cortado", group_places=("p-north",)) == [(0, "p-north", "v-closed", None)]
    assert _said("cortado", group_places=("p-north", "p-bridge")) == []
    assert _said("cortado") == []


def test_a_question_and_two_values_of_a_key_are_doubtful_but_still_suggested():
    assert _said("Acceso Norte abierto?") == [(0, "p-north", "v-open", QUESTION)]
    assert _said("Puente 🔴 abierto") == [
        (0, "p-bridge", "v-closed", TWO_VALUES), (0, "p-bridge", "v-open", TWO_VALUES),
    ]


def test_a_place_without_a_value_or_a_value_without_a_place_suggests_nothing():
    assert _said("¿Alguien sabe cómo está el Acceso Norte?") == []
    assert _said("todo abierto por acá") == []
    assert _said("") == []


def test_marks_on_letters_are_part_of_the_word_and_what_matched_is_given_as_written():
    sindyan = Place("p-s", ("السنديان",))
    found = read(compile_map([sindyan], [CLOSED]), "السنديان مُسَكَّر")
    assert found[0].words == ("السنديان", "مُسَكَّر")


def test_emojis_are_words_of_their_own_with_or_without_the_mark_that_colors_them():
    assert tokens("✅️Puente") == ["✅", "puente"]
    assert _said("Puente ✅️") == [(0, "p-bridge", "v-open", None)]


def test_every_word_of_a_line_that_says_the_same_value_goes_with_its_suggestion():
    found = read(READER, "🔴 Puente cerrado")
    assert [(s.value_id, s.words) for s in found] == [("v-closed", ("Puente", "🔴", "cerrado"))]
