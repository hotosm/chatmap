from recognition.languages import asks, forms, language_of, languages, stem
from recognition.vocabulary import Place, Value, compile_map, read, tokens

KNOWN = languages()


def test_there_is_a_file_for_each_alphabet_and_a_word_is_read_with_the_one_of_its_letters():
    names = {language.name for language in KNOWN}
    assert {"Arabic", "Hebrew"} <= names
    assert language_of("مسكر", KNOWN).name == "Arabic"
    assert language_of("סגור", KNOWN).name == "Hebrew"
    assert language_of("cerrado", KNOWN).name.startswith("Latin")
    assert language_of("170", KNOWN) is None
    assert language_of("✅", KNOWN) is None


def test_prefixes_are_taken_off_only_in_the_language_that_sticks_them():
    assert "تفتيش" in forms("وتفتيش", KNOWN)
    assert "סגור" in forms("והסגור", KNOWN)
    # "b" and "l" are prefixes in Arabic and Hebrew, not in Spanish
    assert forms("bloqueado", KNOWN) == ("bloqueado",)


def test_a_word_with_another_ending_of_its_language_is_the_same_word_but_a_number_is_not():
    assert stem("سالكات", KNOWN) == stem("سالك", KNOWN)
    assert stem("cerrada", KNOWN) == stem("cerrado", KNOWN) == stem("cerrados", KNOWN)
    assert stem("controlado", KNOWN) == stem("control", KNOWN)
    assert stem("סגורה", KNOWN) == stem("סגור", KNOWN)
    assert stem("170", KNOWN) == "170"
    # What is left has to be long enough
    assert stem("pas", KNOWN) == "pas"


def test_a_line_is_a_question_by_its_marks_or_its_question_words_whole():
    assert asks("Acceso Norte abierto?", tokens("Acceso Norte abierto?"), KNOWN)
    assert asks("هل الحاجز مسكر", tokens("هل الحاجز مسكر"), KNOWN)
    assert asks("alguien sabe como esta el puente", tokens("alguien sabe como esta el puente"), KNOWN)
    assert not asks("el puente esta cerrado", tokens("el puente esta cerrado"), KNOWN)


def test_a_message_may_mix_languages_and_each_word_is_read_with_its_own():
    reader = compile_map(
        [Place("p-b", ("Puente",)), Place("p-s", ("السنديان",)), Place("p-g", ("שער",))],
        [Value("v-c", "k", ("cerrado", "مسكر", "סגור"))],
    )
    text = "Puente cerrada\nوالسنديان مسكرين\nשער סגורה"
    assert [(s.line, s.point_id) for s in read(reader, text)] == [(0, "p-b"), (1, "p-s"), (2, "p-g")]


def test_without_language_files_words_only_match_as_they_are():
    reader = compile_map([Place("p-b", ("Puente",))], [Value("v-c", "k", ("cerrado",))], known=())
    assert read(reader, "Puente cerrada") == []
    assert len(read(reader, "Puente cerrado")) == 1
