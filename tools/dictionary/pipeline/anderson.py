# -*- coding: utf-8 -*-
"""Convert Troy Anderson's 1986 ASCII notation to the edition display form.

This is the recovered converter, kept dependency-free and importable by every
pipeline stage. It changes presentation notation; it is not a modernization of
the 1990 lexical content.
"""
import unicodedata

ACUTE = '\u0301'
DOTB = '\u0323'
BREVEB = '\u032f'
RING = '\u0325'
RDOT = '\u00b7'
TIE = '-'
EJEC = '\u0313'
ASP = '\u02bb'
SUP = {'i': 'ⁱ', 'u': 'ᵘ', 'w': 'ʷ', 'a': 'ᵃ', 'e': 'ᵉ', 'n': 'ⁿ', 'y': 'ʸ', 'h': 'ʰ'}
MULTI = [("t'#", "t'ł"), ("t#", 'tł'), ('x;', 'x' + DOTB),
         ('g;', 'g' + DOTB), ('%;', 'ɣ' + DOTB)]
SINGLE = {'e': 'ɛ', '@': 'ə', '#': 'ł', '%': 'ɣ', '$': 'ð', '`': ASP,
          ':': RDOT, '-': TIE, 'N': 'ɴ', 'L': 'ʟ', 'M': 'ᴍ'}
VOWELS = set('aeiouəɛ')


def convert(value):
    out = []
    i = 0
    while i < len(value):
        for key, replacement in MULTI:
            if value.startswith(key, i):
                out.append(replacement)
                i += len(key)
                break
        else:
            ch = value[i]
            if ch == 'v' and i + 1 < len(value):
                nxt = value[i + 1]
                out.append(SUP.get(nxt, nxt))
                i += 2
                continue
            if ch == '<':
                for j in range(len(out) - 1, -1, -1):
                    if out[j] and out[j][-1] in VOWELS:
                        out[j] += ACUTE
                        break
                else:
                    out.append(ACUTE)
            elif ch in ';&0!':
                mark = {';': DOTB, '&': BREVEB, '0': RING, '!': EJEC}[ch]
                for j in range(len(out) - 1, -1, -1):
                    prior = out[j][-1] if out[j] else ''
                    if prior and prior.isalpha() and unicodedata.category(prior) != 'Lm':
                        out[j] += mark
                        break
                else:
                    out.append(mark)
            else:
                out.append(SINGLE.get(ch, ch))
            i += 1
    return unicodedata.normalize('NFC', ''.join(out))


def normalize_target(value):
    value = unicodedata.normalize('NFD', value)
    value = value.replace('´', ACUTE).replace('’', 'ʼ').replace('!', 'ʼ')
    value = value.replace('`', 'ʰ').replace('&', BREVEB).replace('•', RDOT)
    value = value.replace(RDOT + ACUTE, ACUTE + RDOT)
    return unicodedata.normalize('NFC', value)
