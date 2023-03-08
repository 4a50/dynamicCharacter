import nltk
import re

def getNounPhrase(aiResponse):    
    # Process String to remove text between asterisks
    sub_string = re.sub(r'\*.*?\*', '', aiResponse)
    # Break each sentence out into an array.
    print('sub-string -> ' + sub_string)
    sentenceTokenize = nltk.sent_tokenize(sub_string)

    [print('Sentence --> ' + sent) for sent in sentenceTokenize]

    # tag the words in each sentence
    taggedSentenceList = []    
    nounPhrases = []
    for sent in sentenceTokenize:    
        tkens =  nltk.word_tokenize(sent)    
        tged = nltk.pos_tag(tkens)
        taggedSentenceList.append(tged)
        print(tged)
        # find noun phrases according to the regEx
        grammar = "NP: {<JJ>*<NNS>|<NN>}"
        chunkParser = nltk.RegexpParser(grammar)
        chunks = chunkParser.parse(tged)
        for chunk in chunks.subtrees(filter=lambda x: x.label() == 'NP'): # print out all noun phrases        
            np = ' '.join(word for word, tag in chunk.leaves())
            nounPhrases.append(np)
            print('NP = ' + np)
    print('--------')
    print(nounPhrases)
    print('--------')
    return nounPhrases