################################################################################
#  
#  Copyright (C) 2012-2020 Jack Araz, Eric Conte & Benjamin Fuks
#  The MadAnalysis development team, email: <ma5team@iphc.cnrs.fr>
#  
#  This file is part of MadAnalysis 5.
#  Official website: <https://launchpad.net/madanalysis5>
#  
#  MadAnalysis 5 is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  
#  MadAnalysis 5 is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with MadAnalysis 5. If not, see <http://www.gnu.org/licenses/>
#  
################################################################################


import six

class metaclass(type):
        def __getattr__(self, name):
            return list(self.values.keys()).index(name)
        
        def convert2string(self,val):
            name = list(self.values.keys())[val]
            return self.values[name][0]

@six.add_metaclass(metaclass)        
class SBratioType(object):
        values = {'S_OVER_B' : ['S/B'],\
                  'B_OVER_S' : ['B/S'],\
                  'S_OVER_SB': ['S/sqrt(S+B)']}



  

