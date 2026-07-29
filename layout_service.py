import re
from fastapi import FastAPI, Body
from spellchecker import SpellChecker
import pymorphy3

app = FastAPI()

# Словаре загружаются ОДИН РАЗ в оперативную память при старте службы
print("Загрузка локальных словарей в RAM...")
spell_en = SpellChecker(language='en')
spell_ru = SpellChecker(language='ru')
morph_ru = pymorphy3.MorphAnalyzer()
print("Микросервис Smart Switcher успешно запущен и ждет хоткеи!")

def get_char_type(char):
    if char.isspace():
        return "SPACE"
    if re.match(r'[а-яА-ЯёЁ]', char):
        return "CYRILLIC"
    if re.match(r'[a-zA-Z]', char):
        return "LATIN"
    if char in ".,`~<>[]{};:'\"":
        return "PUNCT"
    if char in "!@#$%^&*()_-+=|\\/?":
        return "CODE_SIGN"
    return "OTHER"

def smart_tokenize(text):
    if not text:
        return []
    tokens = []
    current_token = text[0]
    last_type = get_char_type(text[0])
    
    for char in text[1:]:
        current_type = get_char_type(char)
        if current_type == "PUNCT" and last_type in ("LATIN", "CYRILLIC"):
            current_token += char
            continue
        if current_type != last_type and not (last_type == "PUNCT" and current_type in ("LATIN", "CYRILLIC")):
            tokens.append(current_token)
            current_token = char
            last_type = current_type
        else:
            current_token += char
            if current_type != "PUNCT":
                last_type = current_type
    if current_token:
        tokens.append(current_token)
    return tokens

@app.post("/fix")
async def fix_text(payload: dict = Body(...)):
    text = payload.get("text", "")
    if not text:
        return {"result": ""}

    en_to_ru = str.maketrans(
        "qwertyuiop[]asdfghjkl;'zxcvbnm,.QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?`~",
        "йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,ёЁ"
    )
    ru_to_en = str.maketrans(
        "йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,ёЁ",
        "qwertyuiop[]asdfghjkl;'zxcvbnm,.QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?`~"
    )

    tokens = smart_tokenize(text)
    token_objects = []

    def is_valid_russian(word):
        return morph_ru.word_is_known(word.lower())

    for token in tokens:
        is_space = not token or not token.strip()
        is_code = bool(re.match(r'^[.,?!:;()\"\'\-`{}<>\[\]=+*_/]+$', token))
        is_latin = bool(re.match(r'^[a-zA-Z.,!=+*{}\[\]()_`\"\'/~<>#$-;:^]+$', token))
        is_cyrillic = bool(re.match(r'^[а-яА-ЯёЁ.,!=+*{}\[\]()_`\"\'/~<>#$-;:^]+$', token))

        obj = {
            "original": token,
            "text": token,
            "was_inverted": False,
            "is_linguistic": (is_latin or is_cyrillic) and not is_code and not is_space,
            "is_latin": is_latin,
            "is_cyrillic": is_cyrillic
        }

        if is_space or is_code or (not is_latin and not is_cyrillic):
            token_objects.append(obj)
            continue

        has_trailing_punct = token[-1] in '.,!?бюБЮ'
        variants = [{"text": token, "is_stripped": False}]
        if has_trailing_punct:
            variants.append({"text": token[:-1], "is_stripped": True})

        token_fixed = False

        for variant in variants:
            if token_fixed:
                break
                
            current_token = variant["text"]
            token_lower = current_token.lower()
            current_map = en_to_ru if is_latin else ru_to_en
            inverted = current_token.translate(current_map)
            inverted_lower = inverted.lower()

            # 1. Точное совпадение в исходном словаре
            if is_latin and token_lower in spell_en:
                obj["text"] = current_token
                obj["was_inverted"] = False
                token_fixed = True
            elif is_cyrillic and (token_lower in spell_ru or is_valid_russian(current_token)):
                obj["text"] = current_token
                obj["was_inverted"] = False
                token_fixed = True
            
            # 2. Инвертируем раскладку и ищем точное совпадение
            elif is_latin and (inverted_lower in spell_ru or is_valid_russian(inverted)):
                obj["text"] = inverted
                obj["was_inverted"] = True
                token_fixed = True
            elif is_cyrillic and inverted_lower in spell_en:
                obj["text"] = inverted
                obj["was_inverted"] = True
                token_fixed = True
            
            # 3. Опечатщик в исходном языке (Работает ТОЛЬКО на чистом слове без хвостов)
            elif is_latin and len(current_token) > 3:
                if not variant["is_stripped"] and has_trailing_punct:
                    pass
                else:
                    corr = spell_en.correction(token_lower)
                    if corr and corr != token_lower:
                        obj["text"] = corr.upper() if current_token.isupper() else (corr.capitalize() if current_token.istitle() else corr)
                        token_fixed = True
                    else:
                        obj["text"] = current_token
                        
            elif is_cyrillic and len(current_token) > 3:
                if not variant["is_stripped"] and has_trailing_punct:
                    pass
                else:
                    corr = spell_ru.correction(token_lower)
                    if corr and corr != token_lower:
                        obj["text"] = corr.upper() if current_token.isupper() else (corr.capitalize() if current_token.istitle() else corr)
                        token_fixed = True
                    else:
                        obj["text"] = current_token
            
            # 4. Перевертыш + опечатщик (Работает ТОЛЬКО на чистом слове без хвостов)
            elif is_latin and len(current_token) > 3:
                if not variant["is_stripped"] and has_trailing_punct:
                    pass
                else:
                    corr = spell_ru.correction(inverted_lower)
                    if corr and corr != inverted_lower:
                        obj["text"] = corr.upper() if current_token.isupper() else (corr.capitalize() if current_token.istitle() else corr)
                        obj["was_inverted"] = True
                        token_fixed = True
                    else:
                        obj["text"] = current_token
                        
            elif is_cyrillic and len(current_token) > 3:
                if not variant["is_stripped"] and has_trailing_punct:
                    pass
                else:
                    corr = spell_en.correction(inverted_lower)
                    if corr and corr != inverted_lower:
                        obj["text"] = corr.upper() if current_token.isupper() else (corr.capitalize() if current_token.istitle() else corr)
                        obj["was_inverted"] = True
                        token_fixed = True
                    else:
                        obj["text"] = current_token
            else:
                continue

            if token_fixed:
                if variant["is_stripped"]:
                    trailing_char = token[-1]
                    if obj["text"] != current_token:
                        if is_latin:
                            if trailing_char in ',бБ': trailing_char = ','
                            elif trailing_char in '.юЮ': trailing_char = '.'
                        else:
                            if trailing_char in ',бБ': trailing_char = ','
                            elif trailing_char in '.юЮ': trailing_char = '.'
                    obj["text"] = obj["text"] + trailing_char

        token_objects.append(obj)

    # =========================================================================
    # ФИНАЛЬНЫЙ ПРОХОД: Асимметричное контекстное сглаживание (4 ситуации)
    # =========================================================================
    num_tokens = len(token_objects)
    for i in range(num_tokens):
        obj = token_objects[i]
        if not obj["is_linguistic"] or obj["was_inverted"]:
            continue
            
        left_neighbor = None
        for l in range(i - 1, -1, -1):
            if token_objects[l]["is_linguistic"]:
                left_neighbor = token_objects[l]
                break
                
        right_neighbor = None
        for r in range(i + 1, num_tokens):
            if token_objects[r]["is_linguistic"]:
                right_neighbor = token_objects[r]
                break

        left_lang = None
        if left_neighbor:
            if left_neighbor["was_inverted"]:
                left_lang = "CYRILLIC" if left_neighbor["is_latin"] else "LATIN"
            else:
                left_lang = "LATIN" if left_neighbor["is_latin"] else "CYRILLIC"

        right_lang = None
        if right_neighbor:
            if right_neighbor["was_inverted"]:
                right_lang = "CYRILLIC" if right_neighbor["is_latin"] else "LATIN"
            else:
                right_lang = "LATIN" if right_neighbor["is_latin"] else "CYRILLIC"

        has_inverted_neighbor = (left_neighbor and left_neighbor["was_inverted"]) or (right_neighbor and right_neighbor["was_inverted"])
        languages_match_or_single = False
        target_context_lang = None

        if left_lang and right_lang:
            if left_lang == right_lang:
                languages_match_or_single = True
                target_context_lang = left_lang
        elif left_lang:
            languages_match_or_single = True
            target_context_lang = left_lang
        elif right_lang:
            languages_match_or_single = True
            target_context_lang = right_lang

        if has_inverted_neighbor and languages_match_or_single and target_context_lang:
            current_lang = "LATIN" if obj["is_latin"] else "CYRILLIC"
            
            if current_lang != target_context_lang:
                current_map = en_to_ru if obj["is_latin"] else ru_to_en
                inverted_full = obj["original"].translate(current_map)
                
                clean_word = inverted_full.strip('.,?!`"\'')
                clean_word_lower = clean_word.lower()
                
                is_valid = False
                if target_context_lang == "CYRILLIC":
                    if clean_word_lower in spell_ru or is_valid_russian(clean_word):
                        is_valid = True
                elif target_context_lang == "LATIN":
                    if clean_word_lower in spell_en:
                        is_valid = True
                        
                if is_valid:
                    obj["text"] = inverted_full
                    obj["was_inverted"] = True

    return {"result": "".join([t["text"] for t in token_objects])}

@app.post("/invert")
async def blind_invert(payload: dict = Body(...)):
    text = payload.get("text", "")
    if not text:
        return {"result": ""}

    # МАКСИМАЛЬНЫЕ КАРТЫ: ровно 84 символа, включая цифры и спецклавиши обеих раскладок
    en_full = "qwertyuiop[]asdfghjkl;'zxcvbnm,.QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?`~1234567890!@#$%^&*()_+|\\"
    ru_full = "йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,ёЁ1234567890!\"№;%:?*()_+/\\"

    # Проверяем строго наличие национальных букв
    has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', text))
    has_latin = bool(re.search(r'[a-zA-Z]', text))

    # СТРОГАЯ И ЛАКОНИЧНАЯ ЛОГИКА АВТОМАТА КАЛАШНИКОВА:
    if has_cyrillic and not has_latin:
        # Есть ТОЛЬКО русские буквы -> железно переводим RU -> EN
        ru_to_en = str.maketrans(ru_full, en_full)
        result_text = text.translate(ru_to_en)
    elif has_latin and not has_cyrillic:
        # Есть ТОЛЬКО английские буквы -> железно переводим EN -> RU
        en_to_ru = str.maketrans(en_full, ru_full)
        result_text = text.translate(en_to_ru)
    else:
        # Ситуация А: Присутствуют оба алфавита (смешанный текст) -> мы не знаем что делать, ничего не трогаем
        # Ситуация Б: Букв нет вообще (только цифры/знаки кода) -> ничего не трогаем
        result_text = text

    return {"result": result_text}


