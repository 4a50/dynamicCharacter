from datetime import datetime
from pathlib import Path
import sys
import json
import os
rootDir = Path(__file__).resolve().parent.parent.parent
logFileDirectory = Path(f'{rootDir}/logs')
logFile = Path(f"{logFileDirectory}/dynamicCharacterLog.json")
print(logFileDirectory)
if(not logFileDirectory.exists()):
    print('Creating logs Directory')    
    logFileDirectory.mkdir()    


def printf(cat, txt = '', printOut = True):
    
    obj = {"timestamp": str(datetime.now()), "category": cat, "message": txt} 
    if(printOut): print(f'Log: {obj}')          
    fileExist =  logFile.is_file()    
    if(fileExist):        
        with open(logFile, 'r') as f:
            fileJson = json.load(f)        
        fileJson.append(obj)
        with open(logFile, 'w') as f:
            json.dump(fileJson, f)
    else:        
        with open(logFile, 'a') as f:                
            json.dump([obj], f)


