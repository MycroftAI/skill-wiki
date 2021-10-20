# Copyright 2021, Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

def remove_nested_parentheses(input: str) -> str:
    """Remove content contained within parentheses from a string.
    
    This includes content that is nested within multiple sets, eg:
    Lemurs (/ˈliːmər/ (listen) LEE-mər)
    """
    ret = ''
    nest_depth = 0
    for char in input:
        if char == '(':
            nest_depth += 1
        elif (char == ')') and nest_depth:
            nest_depth -= 1
        elif not nest_depth:
            ret += char
    return ret