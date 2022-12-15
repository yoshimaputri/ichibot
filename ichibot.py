from flask import Flask
from flask import request
from flask import Response
import requests
from googletrans import Translator
import wikipedia
from langdetect import detect
import json

conf = json.load(open('config.json', 'r'))
TOKEN = conf['TOKEN']
URL = conf['URL']
app = Flask(__name__)

global hook
global lang
global to_lang
lang = 'en'
hook = False
to_lang = 'en'
ts = Translator()

def parse_message(msg):
    if 'message' in msg:
        chat_id = msg['message']['chat']['id']
        txt = msg['message']['text']
        sender_name = msg['message']['from']['first_name']
    elif 'edited_message' in msg:
        chat_id = msg['edited_message']['chat']['id']
        txt = msg['edited_message']['text']
        sender_name = msg['edited_message']['from']['first_name']
    print(f'\n{sender_name}: {txt}')

    return chat_id, txt, sender_name

def tel_send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    r = requests.post(url, json=payload)

    return r

def trans(text, dest_lang):
    if dest_lang == 'kr':
        dest_lang = 'ko'
    res = ts.translate(text, dest=dest_lang).text
    return res

@app.route('/', methods=['GET','POST'])
def index():
    resp = ''
    global lang
    global hook 
    global to_lang
    if request.method == 'POST':
        if hook == False:
            webhook()
        msg = request.get_json()
        chat_id, message, sender = parse_message(msg)

        # mini features: change language
        if message == '/en':
            lang = 'en'
        elif message == '/kr' or message == '/ko':
            lang = 'ko'

        if message == '/menu':
            with open('feature.txt') as f:
                r = f.readlines()
            for i in r:
                if ':' in i:
                    begin = i.split(':')[0]
                    last = i.replace(begin,'')
                    i = trans(begin, lang) + last
                    resp += f'\t\t\t\t{i}'
                else:
                    i = trans(i, lang)
                    resp += i + '\n'

        elif message == '/start':
            resp = trans(f"Hello, {sender}!\nWelcome to IchiBot!\nChoose language?", lang)
            resp += " '/en' || '/ko'"

        # MAIN FEATURES - 1: Translation Mode
        elif '/ts' in message:
            to_lang = message.split()[1].split('/')[-1]
            if to_lang == 'list':
                with open('langcodes.txt') as f:
                    resp = f.read()
            else:
                message_ = message.split(to_lang)[-1].lstrip()
                # resp = f'translate to ==> {to_lang}'
                resp = trans(message_, to_lang)

        # MAIN FEATURES - 2: Wikipedia Search
        elif '/wk' in message:
            inp_lang = message.count('/')
            exc_lang = ['ar', 'hi', 'ja', 'ko', 'ru', 'vi', 'zh-cn', 'uz', 'en']
            if 'list' in message:
                print('language list in wiki')
                message_ = wikipedia.languages()
                resp = str(message_)
                print(resp)
            else:
                if inp_lang > 1:
                    to_lang = message.split()[1].split('/')[-1]
                    message = message.split(to_lang)[-1].lstrip()
                else:
                    message = message.split('/wk')[-1].lstrip()
                ori_msg = message
                lang_detect = detect(message)
                print('lang detect', lang_detect)
                if lang_detect == to_lang:
                    wikipedia.set_lang(to_lang)
                # change all detect input to ENGLISH -> easier to search in wikipedia
                elif lang_detect not in exc_lang:
                    message = trans(message, 'en')
                    wikipedia.set_lang('en')
                else:
                    wikipedia.set_lang(lang_detect)

                try:
                    most_fit = wikipedia.search(message)[0]
                    print('search for:', most_fit)
                    if lang_detect != to_lang and lang_detect in exc_lang:
                        resp += f'>> {ori_msg} / {trans(most_fit, to_lang)}\n\n'
                    else:
                        resp += f'>> {most_fit.upper()}\n\n'
                    content = wikipedia.summary(most_fit.lower())
                    # translate the result content, based on input language that want to show
                    if lang_detect != to_lang:
                        content = trans(content, to_lang)
                    info = (content[:500] + '..') if len(content) > 500 else content
                    resp += info + '\n\n'
                    resp += wikipedia.page(most_fit).url
                except Exception as e:
                    # resp += f'No word {ori_msg} in general'
                    resp = "Sorry! IchiBot can't process that! ㅠㅠ\n\nError due to: " + str(e)
                    print(e)

        else:
            resp = trans("How can I help you?", lang)
            resp += '\n/menu - '
            resp += trans("to see the list of command", lang)
        
        tel_send_message(chat_id, resp)

        return Response('ok', status=200)
    else:
        return "<h1> Welcome to IchiBot! </h1>"

@app.route("/webhook/")
def webhook():
    global hook
    s = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL}")
    if s:
        hook = True
        return "Success " + str(s)
    else:
        return "Failed"

if __name__ == '__main__':
    app.run(debug=True, port=5002)
