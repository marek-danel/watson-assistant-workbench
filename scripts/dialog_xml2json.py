"""
Copyright 2018 IBM Corporation
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json,sys,argparse,os,re,csv,io,copy
import lxml.etree as LET
from cfgCommons import Cfg
from wawCommons import printf, eprintf
import time
import datetime

# CONSTANTS (care it is not real constant)
DEFAULT_SELECTOR = 'user_input'

DEFAULT_REPEAT_ATTEMPTS = 3
DEFAULT_REPEAT_MESS_TEMPLATES = {}
# yes-no
DEFAULT_REPEAT_YES_NO_TEMPLATE = []
outputNode = LET.Element('output')
outputNode.text = 'Please, write YES or NO.'
DEFAULT_REPEAT_YES_NO_TEMPLATE.append(outputNode)
outputNode = LET.Element('output')
outputNode.text = '<express-as type=\\"Apology\\">Sorry, I still do not understand.</express-as> Please, write YES or NO.'
DEFAULT_REPEAT_YES_NO_TEMPLATE.append(outputNode)
outputNode = LET.Element('output')
outputNode.text = '<express-as type=\\"Apology\\">Sorry, you repeatedly did not write YES or NO.</express-as> Returning to the main menu.'
DEFAULT_REPEAT_YES_NO_TEMPLATE.append(outputNode)
DEFAULT_REPEAT_MESS_TEMPLATES['yes-no'] = DEFAULT_REPEAT_YES_NO_TEMPLATE
# default
DEFAULT_REPEAT_DEFAULT_TEMPLATE = []
outputNode = LET.Element('output')
outputNode.text = '<express-as type=\\"Apology\\">Sorry, I do not understand,</express-as> try it again.'
DEFAULT_REPEAT_DEFAULT_TEMPLATE.append(outputNode)
outputNode = LET.Element('output')
outputNode.text = '<express-as type=\\"Apology\\">Sorry, I still do not understand,</express-as> please try to rephrase what you want.'
DEFAULT_REPEAT_DEFAULT_TEMPLATE.append(outputNode)
outputNode = LET.Element('output')
outputNode.text = '<express-as type=\\"Apology\\">Sorry, we do not understand each other.</express-as> Returning to the main menu.'
DEFAULT_REPEAT_DEFAULT_TEMPLATE.append(outputNode)
DEFAULT_REPEAT_MESS_TEMPLATES['default'] = DEFAULT_REPEAT_DEFAULT_TEMPLATE

DEFAULT_CONDITION_YES = '#CONTROL_YES'
DEFAULT_CONDITION_NO = '#CONTROL_NO'
DEFAULT_CONDITION_ELSE = 'anything_else'
DEFAULT_CONDITION_ABORT = '#CONTROL_ABORT'
DEFAULT_CONDITION_AGAIN = '#CONTROL_AGAIN'
DEFAULT_CONDITION_BACK = '#CONTROL_BACK'

# DEFAULT ABORT
DEFAULT_ABORT = LET.Element('autogenerate')
# propagate
DEFAULT_ABORT.set('propagate','true')
# on
DEFAULT_ABORT.set('on','false')
# message abort
DEFAULT_ABORT_MESSAGE = LET.Element('message')
DEFAULT_ABORT_MESSAGE.text = 'Returning to the main menu.'
DEFAULT_ABORT.append(DEFAULT_ABORT_MESSAGE)
# message abort cannot
DEFAULT_ABORT_MESSAGE_CANNOT = LET.Element('message_cannot')
DEFAULT_ABORT_MESSAGE_CANNOT.text = 'You are already in the main menu.'
DEFAULT_ABORT.append(DEFAULT_ABORT_MESSAGE_CANNOT)

# DEFAULT AGAIN
DEFAULT_AGAIN = LET.Element('autogenerate')
# propagate
DEFAULT_AGAIN.set('propagate','true')
# on
DEFAULT_AGAIN.set('on','false')
# message again
DEFAULT_AGAIN_MESSAGE = LET.Element('message')
DEFAULT_AGAIN_MESSAGE.text = 'Repeating current step again.'
DEFAULT_AGAIN.append(DEFAULT_AGAIN_MESSAGE)
# message again cannot
DEFAULT_AGAIN_MESSAGE_CANNOT = LET.Element('message_cannot')
DEFAULT_AGAIN_MESSAGE_CANNOT.text = 'You are in the main menu, no step to repeat.'
DEFAULT_AGAIN.append(DEFAULT_AGAIN_MESSAGE_CANNOT)

# DEFAULT BACK
DEFAULT_BACK = LET.Element('autogenerate')
# propagate
DEFAULT_BACK.set('propagate','true')
# on
DEFAULT_BACK.set('on','false')
# message back
DEFAULT_BACK_MESSAGE = LET.Element('message')
DEFAULT_BACK_MESSAGE.text = 'Returning to the previsous step.'
DEFAULT_BACK.append(DEFAULT_BACK_MESSAGE)
# message back cannot
DEFAULT_BACK_MESSAGE_CANNOT = LET.Element('message_cannot')
DEFAULT_BACK_MESSAGE_CANNOT.text = 'Can\'t go back because you are in the main menu.'
DEFAULT_BACK.append(DEFAULT_BACK_MESSAGE_CANNOT)
# message back to main
DEFAULT_BACK_MESSAGE_TO_MAIN = LET.Element('message_to_main')
DEFAULT_BACK_MESSAGE_TO_MAIN.text = 'Returning back to the main menu.'
DEFAULT_BACK.append(DEFAULT_BACK_MESSAGE_TO_MAIN)

# DEFAULT REPEAT
DEFAULT_REPEAT = LET.Element('autogenerate')
# propagate
DEFAULT_REPEAT.set('propagate','false')

# DEFAULT GENERIC
DEFAULT_GENERIC = LET.Element('autogenerate')
# propagate
DEFAULT_GENERIC.set('propagate','true')
# on
DEFAULT_GENERIC.set('on','false')

# GLOBAL VARIABLES
counter = 0
firstNode = True
parent_map = {}
rootGlobal = None
schema = None

def replace_config_variables (importTree):
     global config
     replaces = importTree.xpath('//replace')

     for repl in replaces:
         # repl.text  - name of the variable to be replaced
         # getattr(config, repl.text) - value of replacement
         # whole segment <replace>...</replace>
         before="" if repl.getparent().text is None else repl.getparent().text
         if repl.text=='internal_build_date_time':
             middle= unicode(datetime.datetime.now().strftime("%y-%m-%d-%H-%M"))
         else:
            middle=getattr(config, repl.text) if hasattr(config, repl.text) else ""
         after="" if repl.tail is None else repl.tail
         repl.getparent().text = ("" if repl.getparent().text is None else repl.getparent().text) + middle + ("" if repl.tail is None else repl.tail)
         repl.getparent().remove(repl)

def validate(xml):
    global schema, VERBOSE
    try:
        schema.assertValid(xml)
        if VERBOSE: eprintf("XML is valid\n")
    except LET.XMLSchemaError:
        eprintf("Invalid XML %s!\n")


def getNodeWithTheSameCondition(root, testNode):
    testNodeCondition = testNode.find('condition').text if testNode.find('condition') is not None else 'anything_else'
    for node in root.findall('node'):
        nodeCondition = node.find('condition').text if node.find('condition') is not None else 'anything_else'
        if testNodeCondition == nodeCondition:
            return node

def importText(importTree, config):
    imports = importTree.xpath('//importText')
    for imp in imports:
        if VERBOSE: eprintf('Importing %s\n', os.path.join(os.path.dirname(getattr(config, 'common_dialog_main')),*filename))
        filename = imp.text.split('/') 
        fp = io.open(os.path.join(os.path.dirname(getattr(config, 'common_dialog_main')),*filename) ,'r', encoding='utf-8')
        importTxt = fp.read()
        fp.close()
        imp.getparent().text = ("" if imp.getparent().text is None else imp.getparent().text) + importTxt + ("" if imp.tail is None else imp.tail)
        imp.getparent().remove(imp)

def importNodes(root, config):
    global rootGlobal, VERBOSE, names
    # IMPORT AND APPEND NODES
    defaultNode = None
    if len(root) > 0 and (root[len(root)-1].find('condition') is None or (root[len(root)-1].find('condition') is not None and root[len(root)-1].find('condition').text == 'anything_else')):
        # IF LAST NODE DOES NOT HAVE CONDITION OR HAS CONDITION SET TO 'anything_else'
        defaultNode = root[len(root)-1]

    for node in root.findall('import'):
        if VERBOSE: eprintf('Importing %s\n', os.path.join(os.path.dirname(getattr(config, 'common_dialog_main')),node.text))
        importPath = node.text.split('/')
        importTree = LET.parse(os.path.join(os.path.dirname(getattr(config, 'common_dialog_main')),*importPath))
        importText(importTree, config)
        replace_config_variables(importTree)
        
        if schema is not None:
            validate(importTree)

        importRoot = importTree.getroot()
        for importChild in importRoot.findall('node'):
            #eprintf('  Importing node: %s\n', importChild)
            nodeWithTheSameCondition = getNodeWithTheSameCondition(root, importChild)
            """
            if nodeWithTheSameCondition is not None:
                # SKIP NODES WITH SAME CONDITIONS
                #eprintf('    Skipping node (same condition): %s\n', nodeWithTheSameCondition)
                if importChild.find('context') is not None:
                    #eprintf('      Context found for node: %s\n', importChild)
                    if nodeWithTheSameCondition.find('context') is None:
                        #eprintf('      Creating context for node: %s\n', nodeWithTheSameCondition)
                        nodeWithTheSameConditionContext = LET.Element('context')
                        nodeWithTheSameCondition.append(nodeWithTheSameConditionContext)
                    # COPY ALL CONTEXT TO NODE WITH SAME CONDITION
                    for context in importChild.find('context'):
                        #eprintf('      Appending context: %s\n', context)
                        nodeWithTheSameCondition.find('context').append(context)
            else:
                # INSERT NODE

                #eprintf('    Appending node: %s\n', importChild) 
            """
            root.append(importChild)

    if defaultNode is not None:
        # MOVE DEFAULT_NODE TO THE END
        root.remove(defaultNode)
        root.append(defaultNode)

    # PROCESS CHILD NODES
    for node in root.findall('node'):
        children = node.find('nodes')
        if children is not None:
            importNodes(children, config)

def removeAllComments(tree):
    comments = tree.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        p.remove(c)

# When duplicit node is found, exit with error
def findAllNodeNames(tree):
    names = []
    nodesWithNames = tree.xpath('//node[@name]')
    for nodeWithName in nodesWithNames:
        if nodeWithName.get('name') in names:
            eprintf('ERROR: Duplicit node name found: %s\n', nodeWithName.get('name'))
            exit(1)
        else:
            names.append(nodeWithName.get('name'))
    return names

# creates name tag for given node using its 'name' attribute, if there is one,
# otherwise generates first unique combination of 'node_' + number.
def generateNodeName(node, prefix):
    global counter, names
    name = node.find('name')
    if name is None:
        if 'name' in node.attrib:
            nodeName = LET.Element('name')
            nodeName.text = node.get('name')
            node.append(nodeName)
        else:
            while ("node_" + str(counter) in names):
                counter += 1
            nodeName = LET.Element('name')
            nodeName.text = "node_" + str(counter)
            node.append(nodeName)
            counter += 1
#        eprintf('Generate node name: %s\n', nodeName.text)
    if prefix:
        node.find('name').text = prefix + node.find('name').text
    validateNodeName(node)

def validateNodeName(node):
    global names
    name = node.find('name').text
    # check characters (Node names can only contain letters, numbers, hyphens and underscores)
    pattern = re.compile("[\w-]+", re.UNICODE)
    if not pattern.match(name):
        eprintf("Illegal name of the node: '%s'\nNode names can only contain letters, numbers, hyphens and underscores.\n", name)
        exit(1)
#    else:
#        eprintf('\nName of the node:%s is ok.', name)

def isTrue(autogenerate, attributeName):
        attributeValue = autogenerate.get(attributeName)
        if attributeValue == None or attributeValue == 'false':
            return False
        elif attributeValue == 'true':
            return True
        else:
            eprintf('Unknown value of \'%s\' tag: %s.\n', attributeName, attributeValue)
            return False

def isFalse(autogenerate, attributeName):
        attributeValue = autogenerate.get(attributeName)
        if attributeValue == None or attributeValue == 'true':
            return False;
        elif attributeValue == 'false':
            return True
        else:
            eprintf('Unknown value of \'%s\' tag: %s.\n', attributeName, attributeValue)
            return False

def generateNodes(root, parent, parentAbortSettings, parentAgainSettings, parentBackSettings, parentRepeatSettings, parentGenericSettings):
    global parent_map, VERBOSE
    # GENERATE NAMES
    for node in root.findall('node'):
        generateNodeName(node, '')
        if VERBOSE: eprintf('Found node: %s in: %s\n', node.find('name').text, parent.find('name').text if parent is not None else 'root')

    # READ NODES PROPERTIES
    abortSettings = None
    againSettings = None
    backSettings = None
    repeatSettings = None
    genericSettings = None

    for autogenerate in root.findall('autogenerate'):
        if autogenerate.get('type') == 'abort':
            if VERBOSE: eprintf('Abort settings found in parent: %s\n', parent.find('name').text if parent is not None else 'root')
            abortSettings = autogenerate
        if autogenerate.get('type') == 'again':
            if VERBOSE: eprintf('Again settings found in parent: %s\n', parent.find('name').text if parent is not None else 'root')
            againSettings = autogenerate
        if autogenerate.get('type') == 'back':
            if VERBOSE: eprintf('Back settings found in parent: %s\n', parent.find('name').text if parent is not None else 'root')
            backSettings = autogenerate
        if autogenerate.get('type') == 'repeat':
            if VERBOSE: eprintf('Repeat settings found in parent: %s\n', parent.find('name').text if parent is not None else 'root')
            repeatSettings = autogenerate
        if autogenerate.get('type') == 'generic':
            if VERBOSE: eprintf('Generic settings found in parent: %s\n', parent.find('name').text if parent is not None else 'root')
            genericSettings = autogenerate

    abortSettings = mergeSettings(abortSettings, parentAbortSettings)
    # TODO discuss how those funcitonality should work and if it is possible to implement it just in conversation
    #againSettings = mergeSettings(againSettings, parentAgainSettings)
    #backSettings = mergeSettings(backSettings, parentBackSettings)
    repeatSettings = mergeSettings(repeatSettings, parentRepeatSettings)
    genericSettings = mergeSettings(genericSettings, parentGenericSettings)

    # generate if settings exist and are not switched off
    abort = True if (abortSettings is not None and not isFalse(abortSettings, 'on')) else False
    again = True if (againSettings is not None and not isFalse(againSettings, 'on')) else False
    back = True if (backSettings is not None and not isFalse(backSettings, 'on')) else False
    repeat = True if (repeatSettings is not None and not isFalse(repeatSettings, 'on')) else False
    generic = True if (genericSettings is not None and not isFalse(genericSettings, 'on')) else False

    indexOfInsertion = len(root)
    for index in range(0, len(root)):
        node = root[index]
        if node.tag == 'node':
            condition = node.find('condition')
            # TODO check if we generate condition 'anything_else' for nodes without condition
            # we want to generate CONTROL nodes before repeat section
            if condition is None or condition.text == 'anything_else' or condition.text.startswith(('anything_else', '$tries')):
                indexOfInsertion = index
                break;

    # GENERATE NEW NODES
    if abort:
        # ABORT NODE RETURNING TO THE MAIN MENU
        root.insert(indexOfInsertion, generateAbortNode(root, parent, abortSettings))
        indexOfInsertion = indexOfInsertion + 1
    if again:
        # AGAIN NODE REPEAT CURRENT STEP
        root.insert(indexOfInsertion, generateAgainNode(root, parent, againSettings))
        indexOfInsertion = indexOfInsertion + 1
    if back:
        # BACK NODE RETURNING TO PREVIOUS NODE
        root.insert(indexOfInsertion, generateBackNode(root, parent, backSettings))
        indexOfInsertion = indexOfInsertion + 1
    if generic:
        # GENERIC NODE
        for genericChild in genericSettings:
            genericChildCopy = copy.deepcopy(genericChild)
            generateNodeName(genericChildCopy, 'GENERIC_')
            root.insert(indexOfInsertion, genericChildCopy)
            indexOfInsertion = indexOfInsertion + 1
    if repeat:
        generateRepeatNodes(root, parent, repeatSettings)

    for node in root.findall('node'):
        # PROCESS CHILD NODES
        children = node.find('nodes')
        if children is not None:
            # propagate settings only if propagation not switched off
            generateNodes(
                children,
                node,
                abortSettings if abortSettings is not None and not isFalse(abortSettings, 'propagate') else None,
                againSettings if againSettings is not None and not isFalse(againSettings, 'propagate') else None,
                backSettings if backSettings is not None and not isFalse(backSettings, 'propagate') else None,
                repeatSettings if repeatSettings is not None and not isFalse(repeatSettings, 'propagate') else None,
                genericSettings if genericSettings is not None and not isFalse(genericSettings, 'propagate') else None
            )

def mergeSettings(childSettings, parentSettings):
    if childSettings is None:
        if VERBOSE: eprintf('Returning parent settings\n')
        return parentSettings
    if parentSettings is None:
        if VERBOSE: eprintf('Returning child settings\n')
        return childSettings
    # for all child elements
    for element in parentSettings:
        if childSettings.find(element.tag) is None:
            childSettings.append(element)
    # for all attributes
    for attributeName in parentSettings.attrib:
        if childSettings.get(attributeName) is None:
            childSettings.set(attributeName, parentSettings.get(attributeName))
    if VERBOSE: eprintf('Returning merged settings\n')
    return childSettings

def generateAbortNode(root, parent, settings):
    global VERBOSE
    # node
    abortNode = LET.Element('node')
    generateNodeName(abortNode, 'ABORT_')
    if VERBOSE: eprintf('Generate abort node for parent: %s named: %s\n', parent.find('name').text if parent is not None else 'root', abortNode.find('name').text)
    # condition
    abortNodeCondition = LET.Element('condition')
    abortNodeCondition.text = DEFAULT_CONDITION_ABORT + (' and intent.confidence >' + settings.get('confidence') if 'confidence' in settings.attrib else '')

    abortNode.append(abortNodeCondition)
    # output
    abortNodeOutput = LET.Element('output')
    if parent is not None:
        abortNodeOutput.text = settings.find('message').text if settings.find('message') is not None else DEFAULT_ABORT_MESSAGE.text
    else:
        abortNodeOutput.text = settings.find('message_cannot').text if settings.find('message_cannot') is not None else DEFAULT_ABORT_MESSAGE_CANNOT.text
    abortNode.append(abortNodeOutput)
    # goto
    if settings.find('goto') is not None:
        abortNode.append(copy.deepcopy(settings.find('goto')))
    return abortNode

def generateAgainNode(root, parent, settings):
    global VERBOSE
    # node
    againNode = LET.Element('node')
    generateNodeName(againNode ,'AGAIN_')
    if VERBOSE: eprintf('Generate again node for parent: %s named: %s\n', parent.find('name').text if parent is not None else 'root', againNode.find('name').text)
    # condition
    againNodeCondition = LET.Element('condition')
    againNodeCondition.text = DEFAULT_CONDITION_AGAIN + (' and intent.confidence >' + settings.get('confidence') if 'confidence' in settings.attrib else '')
    againNode.append(againNodeCondition)
    # output
    againNodeOutput = LET.Element('output')
    againNodeOutput.text = '$againMessage'
    againNode.append(againNodeOutput)
    # goto
    againNodeGoto = LET.Element('goto')
    againNodeGotoTarget = LET.Element('target')
    againNodeGotoTarget.text = root.find('node').find('name').text
    againNodeGoto.append(againNodeGotoTarget)
    againNode.append(againNodeGoto)
    return againNode

def generateBackNode(root, parent, settings):
    global VERBOSE
    # node
    backNode = LET.Element('node')
    generateNodeName(backNode, 'BACK_')
    if VERBOSE: eprintf('Generate back node for parent: %s named: %s\n', parent.find('name').text if parent is not None else 'root', backNode.find('name').text)
    # condition
    backNodeCondition = LET.Element('condition')
    backNodeCondition.text = DEFAULT_CONDITION_BACK + (' and intent.confidence >' + settings.get('confidence') if 'confidence' in settings.attrib else '')
    backNode.append(backNodeCondition)
    if parent is not None and parent in parent_map and parent_map[parent] in parent_map:
        # output
        backNodeOutput = LET.Element('output')
        backNodeOutput.text = settings.find('message').text if settings.find('message') is not None else DEFAULT_BACK_MESSAGE.text
        backNode.append(backNodeOutput)
        # goto
        backNodeGoto = LET.Element('goto', {'selector':'body'})
        backNodeTarget = LET.Element('target')
        backNodeTarget.text = parent_map[parent_map[parent]].find('name').text
        backNodeGoto.append(backNodeTarget)
        backNode.append(backNodeGoto)
    else:
        # output
        backNodeOutput = LET.Element('output')
        if parent is not None:
            backNodeOutput.text = settings.find('message_to_main').text if settings.find('message_to_main') is not None else DEFAULT_BACK_MESSAGE_TO_MAIN.text
        else:
            backNodeOutput.text = settings.find('message_cannot').text if settings.find('message_cannot') is not None else DEFAULT_BACK_MESSAGE_CANNOT.text
        backNode.append(backNodeOutput)
    return backNode

def generateRepeatNodes(root, parent, settings):
    global VERBOSE
    if parent is None: return
    if VERBOSE: eprintf('Generate repeat nodes for parent: %s START\n', parent.find('name').text if parent is not None else 'root')
    # ADD VARIABLE 'attempts_*' TO PARENT'S CONTEXT AND SET IT TO ZERO (FOR SURE)
    repeatVarName = 'attempts_' + parent.find('name').text.replace('-', '') # remove hyphens (they cause problems in mathematical expressions where they act as minus signs)
    # context
    context = parent.find('context')
    if context is None:
        context = LET.Element('context')
        parent.append(context)
    contextRepeat = LET.Element(repeatVarName, {'type':'number'})
    contextRepeat.text = '0'
    context.append(contextRepeat)
    # goto for repetation
    if root.find('node') is None:
      eprintf('Repeat node without options to input something!!!\n')
    repeatNodeGoto = LET.Element('goto')
    repeatNodeGotoTarget = LET.Element('target')
    repeatNodeGotoTarget.text = root.find('node').find('name').text
    repeatNodeGoto.append(repeatNodeGotoTarget)
    # max attempts
    maxAttempts = int(settings.find('attempts').text) if settings is not None and settings.find('attempts') is not None else DEFAULT_REPEAT_ATTEMPTS
    if VERBOSE: eprintf('maxAttempts: %s\n', maxAttempts)
    # output sentences
    outputs = settings.find('outputs').findall('output') if settings.find('outputs') is not None and len(settings.find('outputs').findall('output')) > 0 else DEFAULT_REPEAT_MESS_TEMPLATES['default'] 
    if VERBOSE: eprintf('nOutputs: %s\n', len(outputs))
    # LAST NODE (RETURNING TO THE MAIN MENU)
    generateRepeatNode(parent, root, outputs[-1], maxAttempts-1, repeatVarName, 0, settings.find('goto'))
    if VERBOSE: eprintf('LAST NODE\n')
    # MIDDLE NODE
    for i in range(min(maxAttempts-1, len(outputs)-1) -1, 0, -1):
        generateRepeatNode(parent, root, outputs[i], i, repeatVarName, '<?$' + repeatVarName +' + 1?>', repeatNodeGoto)
        if VERBOSE: eprintf('MIDDLE NODE number: %d\n', i)
    # FIRST (DEFAULT) NODE
    generateRepeatNode(parent, root, outputs[0], 0, repeatVarName, '<? $' + repeatVarName + ' == null ? 0 : $' + repeatVarName + ' + 1 ?>', repeatNodeGoto)
    if VERBOSE: eprintf('FIRST NODE\n')
    if VERBOSE: eprintf('Generate repeat nodes for parent: %s \n', parent.find('name').text if parent is not None else 'root')

def generateRepeatNode(parent, root, output, attempts, varName, varValue, goto):
    global VERBOSE
    # node
    repeatNode = LET.Element('node')
    generateNodeName(repeatNode, 'REPEAT_')
    if VERBOSE: eprintf('Generate repeat node for parent: %s named: %s START\n', parent.find('name').text if parent is not None else 'root', repeatNode.find('name').text)
    # condition
    repeatNodeCondition = LET.Element('condition')
    repeatNodeCondition.text = ('$' + varName + ' == null or ' if attempts == 0 else '') + '$' + varName + ' >= ' + str(attempts)
    repeatNode.append(repeatNodeCondition)
    # context
    repeatNodeContext = LET.Element('context')
    repeatVariable = LET.Element(varName)
    repeatVariable.text = str(varValue)
    if isinstance(varValue, int):
        repeatVariable.set('type', 'number')
    repeatNodeContext.append(repeatVariable)
    repeatNode.append(repeatNodeContext)
    # output
    repeatNode.append(copy.deepcopy(output))
    # goto
    if goto is not None:
        repeatNode.append(copy.deepcopy(goto))
    root.append(repeatNode)
    if VERBOSE: eprintf('Generate repeat node for parent: %s named: %s END\n', parent.find('name').text if parent is not None else 'root', repeatNode.find('name').text)

def printNodes(root, parent, dialogJSON):
    """Converts parsed XML to JSON structure

    Args:
        root (_Element): root of the parsed XML tree - (typically there is element "nodes" )
        parent (_Element): initially None, then parent
        dialogJSON (string): generated JSON
    """
    global firstNode, VERBOSE
    # PROCESS SIBLINGS
    previousSibling = None
    for nodeXML in root: # for each node in nodes
        if not (nodeXML.tag == 'node' or nodeXML.tag == 'slot' or nodeXML.tag == 'handler' or nodeXML.tag == 'response'):
            continue
        # fix name
        if nodeXML.find('name') is None:
            generateNodeName(nodeXML, '')
        else:
            validateNodeName(nodeXML)
        nodeJSON = {'dialog_node':nodeXML.find('name').text}
        dialogJSON.append(nodeJSON)

        children = []

        # TYPE
        if nodeXML.find('type') is not None:
            nodeJSON['type'] = nodeXML.find('type').text
        elif nodeXML.find('slots') is not None:
            nodeJSON['type'] = "frame"
        # EVENTNAME
        if nodeXML.get('eventName') is not None:
            nodeJSON['event_name'] = nodeXML.get('eventName')
            nodeJSON['type'] = 'event_handler'
        # VARIABLE
        if nodeXML.get('variable') is not None:
            nodeJSON['variable'] = nodeXML.get('variable')
            nodeJSON['type'] = 'slot'
        if nodeXML.tag == 'response':
            nodeJSON['type'] = 'response_condition'
        # CONDITION
        if nodeXML.find('condition') is not None:
            nodeJSON['conditions'] = nodeXML.find('condition').text
        elif 'type' in nodeJSON:
            if nodeJSON['type'] == 'default':
                nodeJSON['conditions'] = DEFAULT_CONDITION_ELSE
            elif nodeJSON['type'] == 'yes':
                nodeJSON['conditions'] = DEFAULT_CONDITION_YES
            elif nodeJSON['type'] == 'no':
                nodeJSON['conditions'] = DEFAULT_CONDITION_NO
            elif nodeJSON['type'] == 'slot' or nodeJSON['type'] == 'response_condition' or nodeJSON['type'] == 'event_handler':
                None
            else:
                nodeJSON['conditions'] = DEFAULT_CONDITION_ELSE
        else:
            nodeJSON['conditions'] = DEFAULT_CONDITION_ELSE
        # OUTPUT
        if nodeXML.find('output') is not None:
            outputNodeXML = nodeXML.find('output')
            for responseNodeXML in outputNodeXML.findall('response'): #responses are translated to seperate nodes
                children.append(responseNodeXML)
                outputNodeXML.remove(responseNodeXML)
            # this should be somewhere in generate
            if outputNodeXML.text: # if any free text - create an element <text> txt </text> out of it and delete it
                if outputNodeXML.text.strip():
                    outputNodeTextXML = LET.Element('text')
                    outputNodeTextXML.text = outputNodeXML.text
                    outputNodeXML.append(outputNodeTextXML)
                    # TODO save againMessage
                outputNodeXML.text = None
            if outputNodeXML.find('textValues') is not None: #rename textValues element to text
                outputNodeTextXML = outputNodeXML.find('textValues')
                outputNodeTextXML.tag = 'text'
            convertAll(nodeJSON, outputNodeXML)
        # CONTEXT
        if nodeXML.find('context') is not None:
            convertAll(nodeJSON, nodeXML.find('context')) 
        # ACTIONS
        if nodeXML.find('actions') is not None:
            actionsXML = nodeXML.find('actions')
            nodeJSON['actions'] = []
            for actionXML in actionsXML.findall('action'):
                actionJSON = {}
                convertAll(actionJSON, actionXML)
                nodeJSON['actions'].append(actionJSON['action'])
        # GO TO
        if nodeXML.find('goto') is not None:
            if nodeXML.find('goto').find('target') is None:
                eprintf('WARNING: missing goto target in node: %s\n', nodeXML.find('name').text)
            elif nodeXML.find('goto').find('target').text == '::FIRST_SIBLING':
                nodeXML.find('goto').find('target').text = next(x for x in root if x.tag == 'node').find('name').text
            gotoJson = {'dialog_node':nodeXML.find('goto').find('target').text}
            gotoJson['selector'] = nodeXML.find('goto').find('selector').text if nodeXML.find('goto').find('selector') is not None else DEFAULT_SELECTOR
            nodeJSON['go_to'] = gotoJson
        # PARENT
        if parent is not None:
            nodeJSON['parent'] = parent.find('name').text
        # PREVIOUS SIBLING
        if previousSibling is not None:
            nodeJSON['previous_sibling'] = previousSibling.find('name').text

        # CLOSE NODE
        previousSibling = nodeXML

        # ADD ALL CHILDREN NODES
        nodes = nodeXML.find('nodes')
        if nodes is not None:
            children.extend(nodes)

        # ADD ALL SLOTS (FRAME FUNCTIONALITY)
        slots = nodeXML.find('slots')
        if slots is not None:
            children.extend(slots)

        # ADD ALL HANDLERS (FRAME FUNCTIONALITY)
        handlers = nodeXML.find('handlers')
        if handlers is not None:
            children.extend(handlers)

        # PROCESS ALL CHILDREN
        if children:
            printNodes(children, nodeXML, dialogJSON)


def convertAll(upperNodeJson, nodeXml):
    """Transform object representation of XML to JSON

    Args:
        upperNodeJson (string): Upper node Json representation, it is both input and output. Output is extended by
            nodeXml translated to JSON
        nodeXml (Element): Parsed XML representation to be translated
    """
    key = nodeXml.tag #key is index/selector to upperNodeJson, it is either name (e.g. generic)
    if type(upperNodeJson) is list:  # or an index of the last element of the array
        key = len(upperNodeJson) - 1

    if not list(nodeXml):
        if nodeXml.text:  # if a single element with text - terminal (string, number or none)
            if nodeXml.text.strip().lower() == 'null':
                upperNodeJson[key] = None
            elif nodeXml.get('type') is not None and nodeXml.get('type') == 'number':
                upperNodeJson[key] = float(nodeXml.text)
            else:
                upperNodeJson[key] = nodeXml.text.strip()
        else:
            upperNodeJson[key] = None
    else:
        #if there is an array of subelements within elemnt - separate elements of each tag value to a separate nodeNameMap field
        upperNodeJson[key] = {}

        # Create nodeNameMap, it is an array of unique tag types in nodeXml, each element is an array containing all elements
        #   of the given tag (it groups elements of nodeXML according to tag)
        nodeNameMap = {}
        for element in nodeXml:
            if element.tag in nodeNameMap: #if tag was seen before, add it to the existing array
                nodeNameMap[element.tag].append(element)
            else: #if tag is seen first time - establish array
                nodeNameMap[element.tag] = [ element ]

        for name in nodeNameMap:
            # structure=listItem attribute  results in generating array rather then object
            #if len(nodeNameMap[name]) == 1 and nodeNameMap[name][0].get('structure') != 'listItem' and name!='values':
            if len(nodeNameMap[name]) == 1 and nodeNameMap[name][0].get('structure') != 'listItem' :
                convertAll(upperNodeJson[key], nodeNameMap[name][0])
            else:
                upperNodeJson[key][name] = []
                for element in nodeNameMap[name]:
                    upperNodeJson[key][name].append(None)  # just to get index
                    convertAll(upperNodeJson[key][name], element)


if __name__ == '__main__':
    printf('\nSTARTING: ' + os.path.basename(__file__) + '\n')
    parser = argparse.ArgumentParser(description='Converts dialog nodes from .xml format to Bluemix conversation service workspace .json format', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-dm','--common_dialog_main', required=False, help='main dialog file with dialogue nodes in xml format')
    parser.add_argument('-c','--common_configFilePaths', help='configuaration file', action='append')
    parser.add_argument('-oc', '--common_output_config', help='output configuration file')
    parser.add_argument('-s', '--common_schema', required=False, help='schema file')
    parser.add_argument('-of', '--common_outputs_directory', required=False, help='directory where the otputs will be stored (outputs is default)')
    parser.add_argument('-od', '--common_outputs_dialogs', required=False, help='name of generated file (dialogs.xml is the default)')
    #CF parameters are specific to Cloud Functions Credentials placement from config file and will be replaced in the future by a separate script
    parser.add_argument('-cfn','--cloudfunctions_namespace', required=False, help='cloud functions namespace')
    parser.add_argument('-cfu','--cloudfunctions_username', required=False, help='cloud functions username')
    parser.add_argument('-cfp','--cloudfunctions_password', required=False, help='cloud functions password')
    parser.add_argument('-cfa','--cloudfunctions_package', required=False, help='cloud functions package')
    parser.add_argument('-v','--common_verbose', required=False, help='verbosity', action='store_true')
    args = parser.parse_args(sys.argv[1:])
    config = Cfg(args);
    VERBOSE = hasattr(config, 'common_verbose')

    if hasattr(config, 'cloudfunctions_namespace') and hasattr(config, 'cloudfunctions_package'):
        setattr(config, 'cloudfunctions_path_to_actions', '/' + '/'.join([getattr(config, 'cloudfunctions_namespace').strip("/"), getattr(config, 'cloudfunctions_package').strip("/")]).strip("/") + '/')

    # load dialogue from XML
    if hasattr(config, 'common_dialog_main'):
        dialogTree = LET.parse(getattr(config, 'common_dialog_main'))
    else:
        dialogTree = LET.parse(sys.stdin)

    # load schema
    schemaDirname, this_filename = os.path.split(os.path.abspath(__file__))
    if not hasattr(config, 'common_schema') or getattr(config, 'common_schema') is None:
        setattr(config, 'common_schema', schemaDirname+'/../data_spec/dialog_schema.xml')
        printf('WARNING: Schema not found, using default path /../data_spec/dialog_schema.xml\n;')
    schemaFile = os.path.join(schemaDirname, getattr(config, 'common_schema'))
    if not os.path.exists(schemaFile):
        eprintf('ERROR: Schema file %s not found.\n', schemaFile)
        exit(1)
    schemaTree = LET.parse(schemaFile)
    schema = LET.XMLSchema(schemaTree)
    validate(dialogTree)

    # process dialog tree
    root = dialogTree.getroot()
    rootGlobal = root
    importNodes(root, config)

    # remove all comments
    removeAllComments(dialogTree)

    # find all node names
    names = findAllNodeNames(dialogTree)

    parent_map = dict((c, p) for p in dialogTree.getiterator() for c in p)
    generateNodes(root, None, DEFAULT_ABORT, DEFAULT_AGAIN, DEFAULT_BACK, DEFAULT_REPEAT, DEFAULT_GENERIC)
    if VERBOSE: eprintf('\n')

    # create dialog structure for JSON
    dialogNodes = []

    # convert XML tree to JSON structure
    printNodes(root, None, dialogNodes)

    if hasattr(config, 'common_outputs_directory') and hasattr(config, 'common_outputs_dialogs'):
        if not os.path.exists(getattr(config, 'common_outputs_directory')):
            os.makedirs(getattr(config, 'common_outputs_directory'))
            print('Created new output directory ' + getattr(config, 'common_outputs_directory'))
        with open(os.path.join(getattr(config, 'common_outputs_directory'), getattr(config, 'common_outputs_dialogs')), 'w') as outputFile:
            outputFile.write(json.dumps(dialogNodes, indent=4))
        printf("File %s created\n", os.path.join(getattr(config, 'common_outputs_directory'), getattr(config, 'common_outputs_dialogs')))
    else:
        print json.dumps(dialogNodes, indent=4)

    if hasattr(config, 'common_output_config'):
        config.saveConfiguration(getattr(config, 'common_output_config'))

    printf('\nFINISHING: ' + os.path.basename(__file__) + '\n')
