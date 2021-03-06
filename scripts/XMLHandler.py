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

import lxml.etree as XML
import unicodedata
import re
from wawCommons import eprintf

'''
Created on Jan 12, 2018
@author: alukes
'''


class XMLHandler(object):


    def __init__(self):
        pass


    def convertDialogData(self, dialogData, intents):
        """ Convert Dialog Data into XML and return pointer to the root XML element. """
        nodesXml = XML.Element('nodes')
        for intent in intents:
            intentData = dialogData.getIntentData(intent)
            if not intentData.generateNodes():
                continue

            # construct the XML structure for each intent
            intent_unaccented = unicodedata.normalize('NFD', intent).encode('ascii', 'ignore')
            node_name = re.compile("[^a-zA-Z\d\s\-\_]").sub("_", intent_unaccented)
            nodeXml = XML.Element('node', name=node_name)

            conditionXml = XML.Element('condition')
            conditionXml.text = intent if intent.startswith(u'#') else u'#' + intent
            nodeXml.append(conditionXml)
                
            nodeXml.append(self._createOutputElement(intentData.getChannelOutputs(), intentData.getButtons()))
            if intentData.getVariables():
                nodeXml.append(self._createContextElement(intentData.getVariables()))
            if intentData.getJumpToTarget() and intentData.getJumpToSelector():
                nodeXml.append(self._createGotoElement(intentData.getJumpToTarget(), intentData.getJumpToSelector()))

            nodesXml.append(nodeXml)

        return nodesXml


    def printXml(self, xmlDocument, prettyPrint=True):
        if prettyPrint:
            return XML.tostring(xmlDocument, pretty_print=prettyPrint, encoding='unicode')
        else:
            return XML.tostring(xmlDocument, method='c14n').decode('utf-8')
        

    def _createOutputElement(self, channels, buttons):
        """ Convert output channels into XML structure. """
        outputXml = XML.Element('output')
        if channels:
            for channelName, channelValues in channels.iteritems():
                if channelName == '1':
                    textValuesXml = XML.Element('textValues')
                    for item in channelValues:
                        textValuesXml.append(self._createXmlElement('values', item))
                        outputXml.append(textValuesXml)
                    continue
    
                output = self._concatenateOutputs(channelValues)
                if channelName == '2':
                    outputXml.append(self._createXmlElement('timeout', output))
    
                elif channelName == '3':
                    outputXml.append(self._createXmlElement('sound', output))
    
                elif channelName == '4':
                    outputXml.append(self._createXmlElement('tts', output))
    
                elif channelName == '5':
                    outputXml.append(self._createXmlElement('talking_head', output))
    
                elif channelName == '6':
                    outputXml.append(self._createXmlElement('paper_head', output))
    
                elif channelName == '7':
                    outputXml.append(self._createXmlElement('graphics', output))
    
                elif channelName == '8':
                    outputXml.append(self._createXmlElement('url', output))
    
                else:
                    eprintf('Warning: Unrecognized channel: %s, value: %s\n', channelName, output)
        
        if buttons:
            genericXml = XML.Element('generic')
            for buttonLabel, buttonValue in buttons.iteritems():
                optionsXml = XML.Element('options')
                optionsXml.append(self._createXmlElement('label', buttonLabel))
                optionsXml.append(self._createXmlElement('value', buttonValue))
                genericXml.append(optionsXml)
            outputXml.append(genericXml)
        
        return outputXml
        

    def _createContextElement(self, variables):
        contextXml = XML.Element('context')
        for name, value in variables.iteritems():
            contextXml.append(self._createXmlElement(name, value))
        return contextXml


    def _createGotoElement(self, target, selector):
        gotoXml = XML.Element('goto')
        gotoXml.append(self._createXmlElement('target', target))
        gotoXml.append(self._createXmlElement('selector', selector))
        return gotoXml


    def _createXmlElement(self, name, value):
        xmlElement = XML.Element(name)
        xmlElement.text = value
        return xmlElement
    

    def _concatenateOutputs(self, channelOutputs):
        output = u''
        for segment in channelOutputs:
            output += segment + u' '
        return output.strip()
