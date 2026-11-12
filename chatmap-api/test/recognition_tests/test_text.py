from recognition.text import plain


def test_a_text_is_compared_without_case_nor_accents():
    assert plain("Acceso NORTE cerrádo") == plain("acceso norte cerrado")


def test_a_word_stretched_to_stress_it_is_the_same_word_but_a_number_is_not():
    assert plain("cerrrrrado") == plain("cerrado")
    assert plain("مسكررررر") == plain("مسكر")
    assert plain("ruta 100") != plain("ruta 10")


def test_arabic_is_compared_however_it_is_typed():
    # Vowel marks and shadda, hamza on alef, waw and yeh, and the tatweel that stretches a word
    assert plain("مُسَكَّر") == plain("مسكر") == plain("مسكـــر")
    assert plain("أُغلِق") == plain("إغلق") == plain("اغلق")
    assert plain("سؤال") == plain("سوال")
    # Alef maqsura and ta marbuta, and the Persian yeh and keheh of some keyboards
    assert plain("مستشفى") == plain("مستشفي") == plain("مستشفی")
    assert plain("البوابة") == plain("البوابه")
    assert plain("کبير") == plain("كبير")
    # Arabic-Indic and Persian digits as the ones most people type
    assert plain("طريق ٦٠") == plain("طريق ۶۰") == "طريق 60"
    # The marks that only say where text runs or joins
    assert plain("\u200fمغلق\u200c") == plain("مغلق")


def test_hebrew_is_compared_without_niqqud_with_plain_quotes_and_its_final_letters():
    assert plain("סָגוּר") == plain("סגור")
    assert plain("צה״ל") == plain('צה"ל')
    # A word ending in a final letter is found in its plural, where that letter is not final
    assert plain("מחסום") in plain("מחסומים")
