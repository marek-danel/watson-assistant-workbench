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

import re
from wawCommons import eprintf
from collections import OrderedDict

'''
Created on Jan 15, 2018
@author: alukes
'''

class IntentData(object):
    """ Represents a data structure containing all necessary information for a single Dialog intent. """


    def __init__(self):
        self._alternatives = []  # list of all text alternatives of intent
        self._channels = {}  # key: channel name, value: list of all outputs for the channel
        self._variables = {}  # key: variable name, value: variable value
        self._jumptoTarget = None
        self._jumptoSelector = None
        self._rawOutputs = []  # list of all outputs from the right column of the Excel source
        self._buttons = OrderedDict()  # key: button label, value: full button value

        
    def addIntentAlternative(self, intentAlternative):
        self._alternatives.append(intentAlternative)


    def getIntentAlternatives(self):
        return self._alternatives


    def addChannelOutput(self, channelName, channelOutput):
        if channelName not in self._channels:
            self._channels[channelName] = []
        self._channels[channelName].append(channelOutput)


    def getChannelOutputs(self):
        return self._channels


    def addVariable(self, name, value):
        self._variables[name] = value


    def getVariables(self):
        return self._variables

    
    def setJumpTo(self, target, selector):
        self._jumptoTarget = target
        self._jumptoSelector = selector


    def getJumpToTarget(self):
        return self._jumptoTarget


    def getJumpToSelector(self):
        return self._jumptoSelector


    def addButton(self, label, value):
        self._buttons[label] = value


    def getButtons(self):
        return self._buttons


    def addRawOutput(self, rawOutputs, labelsMap):
        """ Read the raw output and store all data from it - 
            channel outputs, context variables and jumpto definitions. """
        self._rawOutputs.append(rawOutputs)
        if not isinstance(rawOutputs, tuple) or len(rawOutputs) < 1:
            eprintf('Warning: rawOutput does not contain any data: %s\n', rawOutputs)
        
        for item in re.split('%%', rawOutputs[0]):
            if not item: continue
            if item.startswith(u'$'):
                self.__handleVariableDefinition(item[1:])
            elif item.startswith(u'B'):
                self.__handleButtonDefinition(item[1:])
            elif item.startswith(u':'):
                self.__handleJumpToDefinition(item[1:], labelsMap)
            else:
                self.__handleChannelDefinition(item)

        if len(rawOutputs) >= 3:
            if rawOutputs[1]:
                self.__handleButtonDefinition(rawOutputs[1])
            if rawOutputs[2]:
                self.__handleJumpToDefinition(rawOutputs[2], labelsMap)


    def generateNodes(self):
        return self._channels or self._buttons


    def __handleVariableDefinition(self, variables):
        for varAssignment in re.split(';', variables):
            keyAndValue = re.split('=', varAssignment)
            if len(keyAndValue) == 2:
                self.addVariable(keyAndValue[0], keyAndValue[1])


    def __handleJumpToDefinition(self, jumpto, labelsMap):
        selector = 'user_input'
        label = jumpto
        if len(jumpto) > 2 and jumpto[1] == '_':
            label = jumpto[2:]
            if jumpto[0] == 'b':
                selector = 'body'
            elif jumpto[0] == 'c':
                selector = 'condition'

        if label not in labelsMap:
            eprintf('Warning: using jumpto label that was not defined before: %s\n', label)
        else:
            self.setJumpTo(labelsMap[label], selector)


    def __handleChannelDefinition(self, channel):
        channelName = '1'
        channelValue = channel

        if isinstance(channel, str):
            channel = channel.decode('utf-8')
        if unicode.isdigit(channel[0]):
            channelName = channel[0]
            channelValue = channel[1:]

        self.addChannelOutput(channelName, channelValue)


    def __handleButtonDefinition(self, buttons):
        for button in re.split(';', buttons):
            labelAndValue = re.split('=', button)
            if len(labelAndValue) == 2:
                self.addButton(labelAndValue[0].strip(), labelAndValue[1].strip())
