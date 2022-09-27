from fugashi import Tagger
import requests
import json
import time
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

reg = re.compile(r'[a-zA-Z]')

def translate(text):
    tagger = Tagger('-Owakati')
    tagger.parse(text)

    after_spacing_original = ''
    after_spacing_kana = ''

    for word in tagger(text):
        if word.surface in ['、', '。', '､', '｡', '　', "'", "?", "!",'"',',','.']:
            after_spacing_original += word.surface + ' '
            after_spacing_kana += ' '
            continue

        if reg.match(word.surface):
            after_spacing_original += word.surface + ' '
            after_spacing_kana += word.surface + ' '
            continue
        
        # print(word, word.feature.kana, word.feature.lemma, word.pos, sep='\t')
        tags = word.pos.split(',')
        processed = False
        
        if(word.feature.kana is None):
            word_kana = word.surface
        else:
            word_kana = word.feature.kana
        
        for tag in tags:
            if tag == '普通名詞': # 일반 명사
                after_spacing_original += word.surface
                after_spacing_kana += word_kana
                processed = True
                break

            elif tag == '名詞': # 명사
                after_spacing_original += word.surface
                after_spacing_kana += word_kana
                processed = True
                break
            
            elif tag == '助詞' or tag == '助動詞' or tag == '接尾辞': # 조사 or 조동사 or 접미사
                after_spacing_original = after_spacing_original.rstrip()
                after_spacing_kana = after_spacing_kana.rstrip()

                after_spacing_original += word.surface + ' '
                
                if(word.surface == 'は'):
                    after_spacing_kana += 'ワ '
                else:
                    after_spacing_kana += word_kana + ' '
                
                processed = True
                break

            elif tag == '接頭辞': #접두사
                after_spacing_original += word.surface
                after_spacing_kana += word_kana
                processed = True
                break

        if not processed:
            after_spacing_original += word.surface + ' '
            after_spacing_kana += word_kana + ' '

    # print('Original: ', text)
    # print('After spacing: ', after_spacing_original)
    # print('After spacing kana: ', after_spacing_kana)

    return {
        'original': text,
        'after_spacing': after_spacing_original.strip(),
        'after_spacing_kana': after_spacing_kana.strip()
    }


class Item(BaseModel):
    query: str

@app.post("/convert")
async def convert_lyrics(item: Item):
    query = item.query
    split = query.split('\n')
    start = time.time()
    lyrics = {}
    to_kor_lyrics = []
    for i in range(len(split)):
        lyric = translate(split[i])
        lyrics[i] = lyric

        lyric_kor = {
            'id': i,
            'kana': lyric['after_spacing_kana'],
        }
        to_kor_lyrics.append(lyric_kor)

    # j2 request
    response = requests.post('http://localhost:5000/pronounciation/j2k/group', json={'data':to_kor_lyrics})
    response_json = response.json()
    for i in range(len(response_json)):
        lyrics[i]['kor'] = response_json[i]['Pronounce'].strip()

    return {
        # 'original': query,
        'time': time.time() - start,
        'data': lyrics
    }