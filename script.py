import gradio as gr
import modules.shared as shared
import modules.chat
import json
from modules.chat import clean_chat_message
from modules.extensions import apply_extensions
from modules.text_generation import encode, get_max_prompt_length
from extensions.dynamicCharacter.logger import printf
from pathlib import Path
from extensions.dynamicCharacter.nltk_func import getNounPhrase as nltk_txt

import os
import re
params = {
    "activate": False,
    "bias string": " *I am so happy*",
    "context_text_area": None
    }
characterParams = {
    "selected": '',
    "select_list": ['None Selected'],
    "is_select_active": False,
    "enable_override": True,
    "current_context": '',
    "learning_key_words": {},
    "context_first_load": True,
    "refresh_context": False,
    "file_path": ''
}
script_path_dir = os.path.dirname(__file__)


def getCharacterContext(characterInfo):   
    
    wppString = f'[{characterInfo["type"]}(\"{characterInfo["name"]}\")\n'
    wppString += '{\n'
    for p in characterInfo['properties']:
        wppString += p + '('
        wppString += _concatItems(characterInfo['properties'][p], '+')
        wppString += ')\n'
    wppString += '}]'
    return wppString

def _concatItems(arr, charSeparator, useQuotes = True):
    outString = ''
    for i in range(len(arr)):        
        if (i < len(arr) - 1):
                if (useQuotes):
                    outString +=  '\"'+ arr[i] + '\"' + charSeparator
                else:
                    outString +=  arr[i] + charSeparator
        else:
            if(useQuotes):
                outString += '\"' + arr[i] + '\"'
            else:
                outString += arr[i]
    return outString

def input_modifier(string):
    """
    This function is applied to your text inputs before
    they are fed into the model.
    """
    # printf('extension->input_modifier|parameters', string)

    return string

def output_modifier(string):
    # This will analyze for keywords to determine if the character should be updated with likes.
    # TODO: Need to put some limits on the length of the character, it would take up to many tokens, but perhaps able so create
    # character WPP subsets to suit the occasions.  Will help with persisitant memories.
    
    learningKW = _concatItems(characterParams['learning_key_words'], '|', False)
    regex = "(?<=I).*?(?=" + learningKW + ")"
    # printf('Learning REGEX', regex)        
    if(re.search(regex, string)):        
        npList = nltk_txt(string)             
        _update_custom_context(npList)
    return string

def _update_custom_context(npList = None):    
    if(npList or len(npList) > 0):        
        
        with open(characterParams['file_path'], 'r') as f:
            jsonLoad = json.load(f) 
        printf('_updateCustomContext|jsonLoad', jsonLoad)

        _filter_np_and_update_characteristics(npList, jsonLoad["context"]["properties"]["Loves"])
        printf('_updateCustomContext|filtered', jsonLoad["context"]["properties"]["Loves"])
        # [jsonLoad["context"]["properties"]["Loves"].append(lv) for lv in npList]
        
        with open(characterParams['file_path'], 'w') as f:
            json.dump(jsonLoad, f)
        
        characterParams['current_context'] = getCharacterContext(jsonLoad["context"])
        printf('custom Context updated', characterParams['current_context'])

def _filter_np_and_update_characteristics(npList, currentList):
    
    printf(f' _filter_np_list|pre-de-dupe npList|len: {len(npList)}', npList)
    npList = list(set(npList))
    printf(f' _filter_np_list|post-de-dupe npList|len: {len(npList)}', npList)    
    currentList = list(set([currentList.append(x)for x in npList]))
    printf(f' _filter_np_list|post filter and update|len: {len(currentList)}', currentList)    
            
def bot_prefix_modifier(string):
    """
    This function is only applied in chat mode. It modifies
    the prefix text for the Bot and can be used to bias its
    behavior.
    """
    # printf('extension->bot_prefix_modifier|parameters', string)
    # printf('extension->bot_prefix_modifier|character_selected',
        # characterParams['selected'])
    if params['activate'] == True:
        return f'{string} {params["bias string"].strip()} '
    else:
        return string

def _pass_through_prompt_generation(user_input, max_new_tokens, name1, name2, context, chat_prompt_size, impersonate=False):
    user_input = clean_chat_message(user_input)
    rows = [f"{context.strip()}\n"]

    if shared.soft_prompt:
        chat_prompt_size -= shared.soft_prompt_tensor.shape[1]
    max_length = min(get_max_prompt_length(max_new_tokens), chat_prompt_size)

    i = len(shared.history['internal'])-1
    while i >= 0 and len(encode(''.join(rows), max_new_tokens)[0]) < max_length:
        rows.insert(1, f"{name2}: {shared.history['internal'][i][1].strip()}\n")
        if not (shared.history['internal'][i][0] == '<|BEGIN-VISIBLE-CHAT|>'):
            rows.insert(1, f"{name1}: {shared.history['internal'][i][0].strip()}\n")
        i -= 1

    if not impersonate:
        rows.append(f"{name1}: {user_input}\n")
        rows.append(apply_extensions(f"{name2}:", "bot_prefix"))
        limit = 3
    else:
        rows.append(f"{name1}:")
        limit = 2

    while len(rows) > limit and len(encode(''.join(rows), max_new_tokens)[0]) >= max_length:
        rows.pop(1)

    prompt = ''.join(rows)
    return prompt

def custom_generate_chat_prompt(user_input, max_new_tokens, name1, name2, context, chat_prompt_size, impersonate=False):    
    characterParams['file_path'] = charPath = os.path.join(script_path_dir, characterParams['selected'], 'character.json')    
    # printf('extension->custom_generate_chat_prompt|contextIn', context)
    
    if(characterParams['enable_override'] and os.path.exists(charPath)):
        # printf('extension->custom_generate_chat_prompt|IfStatemetn-charPath', charPath)
        if(characterParams['context_first_load']):
            with open(charPath) as f:
                charJson = json.load(f)            
            characterParams['learning_key_words'] = charJson["learning_keywords"]
            characterParams['current_context'] = context = getCharacterContext(charJson["context"])
            
            characterParams['context_first_load'] = False            
            shared.settings['context_pygmalion'] = context
            shared.settings['context'] = context
            
        elif(characterParams['enable_override']):
            context = characterParams['current_context']
    
    newPrompt = _pass_through_prompt_generation(user_input, max_new_tokens, name1, name2, context, chat_prompt_size, impersonate)
    # printf('extension|newPrompt', newPrompt)
    return newPrompt

def generateInitialCharacterParams():
    nameList = []
    for f in os.scandir( script_path_dir):
        if (f.is_dir() 
            and not f.name.startswith('__') 
            and not f.name.startswith('.')
            and not f.name.startswith('custom')):            
                nameList.append(f.name)
        characterParams['select_list'] = nameList
    print('script.py->generateInitialCharacterParams|characterParams[select_list]',
           characterParams['select_list'])    
    if (len(characterParams['select_list']) > 0):
        characterParams['selected'] = characterParams['select_list'][0]

def ui():
    # Get Character Choices
    generateInitialCharacterParams()
    if (len(characterParams["select_list"]) > 0):
        characterParams['is_select_active'] = True
    # printf('script.py->ui|params[character_select_active]',
        #    characterParams['is_select_active'])

    # Gradio elements
    activate = gr.Checkbox(
        value=params['activate'], label='Activate character bias')
    string = gr.Textbox(value=params["bias string"], label='Character bias')
    charOverride = gr.Checkbox(
        value=characterParams['enable_override'], label='Override Character Context')                            
    selectCharacter = gr.Dropdown(
        choices=characterParams['select_list'], label='Custom Character', value=characterParams['selected'])
    # params['context_text_area'] = gr.TextArea(label="Current Context", value=characterParams['current_context'], interactive=False)
    refreshContext = gr.Button(value="Refresh Character Context")

    # Event functions to update the parameters in the backend
    string.change(lambda x: params.update({"bias string": x}), string, None)
    activate.change(lambda x: params.update({"activate": x}), activate, None)
    charOverride.change(lambda x: characterParams.update({"enable_override": x}), charOverride, None)
    selectCharacter.change(lambda x: characterParams.update(
        {"selected": x}), selectCharacter, None)
    refreshContext.click(_update_custom_context)
    
