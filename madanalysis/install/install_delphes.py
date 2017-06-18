################################################################################
#  
#  Copyright (C) 2012-2016 Eric Conte, Benjamin Fuks
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


from madanalysis.install.install_service    import InstallService
from madanalysis.system.user_info           import UserInfo
from madanalysis.system.config_checker      import ConfigChecker
from madanalysis.IOinterface.library_writer import LibraryWriter
from madanalysis.IOinterface.folder_writer  import FolderWriter
from madanalysis.system.checkup             import CheckUp
from shell_command import ShellCommand
from string_tools  import StringTools
import os
import sys
import logging
import glob
import shutil

class InstallDelphes:

    def __init__(self,main):
        self.main        = main
        self.toolsdir    = os.path.normpath(self.main.archi_info.ma5dir+'/tools')
        self.installdir  = os.path.normpath(self.toolsdir+'/delphes')
        self.tmpdir      = self.main.session_info.tmpdir
        self.downloaddir = self.main.session_info.downloaddir
        self.untardir    = os.path.normpath(self.tmpdir + '/MA5_delphes/')
        self.ncores      = 1
#        self.files = {"delphes.tar.gz" : "http://cp3.irmp.ucl.ac.be/downloads/Delphes-3.1.1.tar.gz"}
#        self.files = {"delphes.tar.gz" : "http://cp3.irmp.ucl.ac.be/downloads/Delphes-3.3.0.tar.gz"}
#        self.files = {"delphes.tar.gz" : "http://cp3.irmp.ucl.ac.be/downloads/Delphes-3.3.1.tar.gz"}
#        self.files = {"delphes.tar.gz" : "http://cp3.irmp.ucl.ac.be/downloads/Delphes-3.3.3.tar.gz"}
        self.files = {"delphes.tar.gz" : "http://cp3.irmp.ucl.ac.be/downloads/Delphes-3.4.1.tar.gz"}
#https://madanalysis.irmp.ucl.ac.be/attachment/wiki/WikiStart/Delphes-3.4.1.tar.gz
        self.logger = logging.getLogger('MA5')


    def Detect(self):
        if not os.path.isdir(self.toolsdir):
            self.logger.debug("The folder '"+self.toolsdir+"' is not found")
            return False
        if not os.path.isdir(self.installdir):
            self.logger.debug("The folder "+self.installdir+"' is not found")
            return False
        return True


    def Remove(self,question=True):
        from madanalysis.IOinterface.folder_writer import FolderWriter
        return FolderWriter.RemoveDirectory(self.installdir,question)


    def GetNcores(self):
        self.ncores = InstallService.get_ncores(self.main.archi_info.ncores,\
                                                self.main.forced)


    def CreatePackageFolder(self):
        if not InstallService.create_tools_folder(self.toolsdir):
            return False
        if not InstallService.create_package_folder(self.toolsdir,'delphes'):
            return False
        return True


    def CreateTmpFolder(self):
        ok = InstallService.prepare_tmp(self.untardir, self.downloaddir)
        if ok:
            self.tmpdir=self.untardir
        return ok


    def Download(self):
        # Checking connection with MA5 web site
        if not InstallService.check_ma5site():
            return False
        # Launching wget
        logname = os.path.normpath(self.installdir+'/wget.log')
        if not InstallService.wget(self.files,logname,self.downloaddir):
            return False
        # Ok
        return True


    def Unpack(self):
        # Logname
        logname = os.path.normpath(self.installdir+'/unpack.log')
        # Unpacking the tarball
        ok, packagedir = InstallService.untar(logname, self.downloaddir,self.tmpdir,'delphes.tar.gz')
        if not ok:
            return False
        # Getting the list of files
        self.logger.debug('Getting the list of files ...')
        myfiles=glob.glob(packagedir+'/*')
        self.logger.debug('=> '+str(myfiles))
        # Moving files from packagedir to installdir
        self.logger.debug('Moving files from '+packagedir+' to '+self.installdir+' ...')
        for myfile in myfiles:
            myfile2=myfile.split('/')[-1]
            if os.path.isdir(myfile):
                try:
                    shutil.copytree(myfile,self.installdir+'/'+myfile2)
                except:
                    self.logger.error('impossible to move the file/folder '+myfile+' from '+packagedir+' to '+self.installdir)
                    return False
            else:
                try:
                    shutil.copy(myfile,self.installdir+'/'+myfile2)
                except:
                    self.logger.error('impossible to move the file/folder '+myfile+' from '+packagedir+' to '+self.installdir)
                    return False

        # Updating Makefile
        filename = self.installdir+'/Makefile'
        self.logger.debug('Updating files '+filename+ ': no CMSSW\n')
        self.SwitchOffCMSSW(filename)
        
        filename = self.installdir+'/doc/genMakefile.tcl'
        self.logger.debug('Updating files '+filename+ ': no CMSSW\n')
        self.SwitchOffCMSSW(filename)

        # Updating ExRootTask
        filename = self.installdir+'/external/ExRootAnalysis/ExRootTask.cc'
        self.logger.debug('Updating files: commenting out lines in: '+filename+' ...')
        self.CommentLines(filename,[64,65,66],'//')
        
        # Updating ExRootTask
        filename = self.installdir+'/external/ExRootAnalysis/ExRootConfReader.cc'
        self.logger.debug('Updating files: commenting out lines in: '+filename+' ...')
        self.CommentLines(filename,[178,189,180],'//')

        # Adding files
        filesToAdd = ["MA5GenParticleFilter"]
        if not self.CopyFiles(filesToAdd):
            return False
        if not self.UpdateDictionnary(filesToAdd):
            return False
        
        # Ok
        return True


    def Configure(self):

        # KNOWn DELPHES ISsues: GENERATE ISSUES BECAuse IT USES TCSLSH COMMAND
        
        # Input
        theCommands=['./configure']
        logname=os.path.normpath(self.installdir+'/configuration.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)

        # return result
        if not ok:
            self.logger.error('impossible to configure the project. For more details, see the log file:')
            self.logger.error(logname)
        return ok

        
    def BuildOld(self):

        # Input
        theCommands=['make','ClassesDict_rdict.pcm','ExRootAnalysisDict_rdict.pcm', 'ModulesDict_rdict.pcm', 'FastJetDict_rdict.pcm']
        logname=os.path.normpath(self.installdir+'/compilation_Dict.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            pass # only for ROOT6

        # Input
        theCommands=['make','-j'+str(self.ncores),'libDelphes.so']
        logname=os.path.normpath(self.installdir+'/compilation_libDelphes.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to build the project. For more details, see the log file:')
            self.logger.error(logname)
            return ok

        # Input
        theCommands=['make','DelphesSTDHEP']
        logname=os.path.normpath(self.installdir+'/compilation_STDHEP.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to build the project. For more details, see the log file:')
            self.logger.error(logname)
            return ok

        # Input
        theCommands=['make','DelphesLHEF']
        logname=os.path.normpath(self.installdir+'/compilation_LHEF.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to build the project. For more details, see the log file:')
            self.logger.error(logname)
            return ok

        # Input
        theCommands=['make','DelphesHepMC']
        logname=os.path.normpath(self.installdir+'/compilation_HepMC.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to build the project. For more details, see the log file:')
            self.logger.error(logname)
        return ok


    def Build(self):

        # Input
        theCommands=['make']
        logname=os.path.normpath(self.installdir+'/compilation.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to build the project. For more details, see the log file:')
            self.logger.error(logname)
        return ok


    def Clean(self):
        # Input
        theCommands=['make','clean']
        logname=os.path.normpath(self.installdir+'/clean.log')
        # Execute
        self.logger.debug('shell command: '+' '.join(theCommands))
        ok, out= ShellCommand.ExecuteWithLog(theCommands,\
                                             logname,\
                                             self.installdir,\
                                             silent=False)
        # return result
        if not ok:
            self.logger.error('impossible to clean the project. For more details, see the log file:')
            self.logger.error(logname)
        return ok



    def Check(self):
        # Check folders
        dirs = [self.installdir+"/modules",\
                self.installdir+"/classes"]
        for dir in dirs:
            if not os.path.isdir(dir):
                self.logger.error('folder '+dir+' is missing.')
                self.display_log()
                return False

        # Check one header file
        if not os.path.isfile(self.installdir+'/modules/ParticlePropagator.h'):
            self.logger.error("header labeled 'modules/ParticlePropagator.h' is missing.")
            self.display_log()
            return False

        if not os.path.isfile(self.installdir+'/libDelphes.so')\
          and not os.path.isfile(self.installdir+'/libDelphes.a')\
          and not os.path.isfile(self.installdir+'/libDelphes.dylib'):
            self.logger.error("A delphes library ('libDelphes.so', 'libDelphes.dylib' or 'libDelphes.a') is missing.")
            self.display_log()
            return False

        return True

    def display_log(self):
        self.logger.error("More details can be found into the log files:")
        self.logger.error(" - "+os.path.normpath(self.installdir+"/wget.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/unpack.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/configuration_libDelphes.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/configuration_LHEF.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/configuration_STDHEP.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/configuration_HepMC.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/compilation.log"))
        self.logger.error(" - "+os.path.normpath(self.installdir+"/clean.log"))

    def NeedToRestart(self):
        return True
    
        
    def CommentLines(self,filename,thelines,charac='//'):
        # open input file
        try:
            input = open(filename)
        except:
            self.logger.error("impossible to read the file:" + filename)
            return False

        # open output file
        try:
            output = open(filename+'.savema5','w')
        except:
            self.logger.error("impossible to read the file:" + filename+'.savema5')
            return False

        # lines
        ind = 0
        for line in input:
            ind+=1
            if ind in thelines:
                output.write(charac+' '+line)
            else:
                output.write(line)

        #close
        input.close()
        output.close()

        try:
            shutil.copy(filename+'.savema5',filename)
        except:
            self.logger.error("impossible to copy "+filename+'.savema5 in '+filename)
            return False

        return True

            
    def SwitchOffCMSSW(self,filename):
        # open input file
        try:
            input = open(filename)
        except:
            self.logger.error("impossible to read the file:" + filename)
            return False

        # open output file
        try:
            output = open(filename+'.savema5','w')
        except:
            self.logger.error("impossible to read the file:" + filename+'.savema5')
            return False

        # lines
        for line in input:
            output.write(line.replace('HAS_CMSSW = true','HAS_CMSSW = false'))

        #close
        input.close()
        output.close()

        try:
            shutil.copy(filename+'.savema5',filename)
        except:
            self.logger.error("impossible to copy "+filename+'.savema5 in '+filename)
            return False

        return True


    def CopyFiles(self,filesToAdd):

        for file in filesToAdd:

            inputname  = self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/Interfaces/delphes/'+file+'.cc.install'
            outputname = self.installdir+'/modules/'+file+'.cc'
            self.logger.debug("Copying file from '"+inputname+"' to '"+outputname+'" ...')

            try:
                shutil.copy(inputname,outputname)
            except:
                self.logger.error("impossible to copy "+inputname+' in '+outputname)
                return False
             
            inputname  = self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/Interfaces/delphes/'+file+'.h.install'
            outputname = self.installdir+'/modules/'+file+'.h'
            self.logger.debug("Copying file from '"+inputname+"' to '"+outputname+'" ...')

            try:
                shutil.copy(inputname,outputname)
            except:
                self.logger.error("impossible to copy "+inputname+' in '+outputname)
                return False

            return True


    def UpdateDictionnary(self,filesToAdd):

        inputname = self.installdir+'/modules/ModulesLinkDef.h'
        self.logger.debug("Updating the Delphes dictionnary '"+inputname+'" ...')
        try:
            input = open(inputname)
        except:
            self.logger.error('impossible to open '+inputname)
            return False

        outputname = self.installdir+'/modules/ModulesLinkDef.savema5'
        try:
            output = open(outputname,'w')
        except:
            self.logger.error('impossible to write '+outputname)
            return False

        for line in input:
            myline = line.lstrip()
            myline = myline.rstrip()
            words = myline.split()

            if len(words)>=2:
                if words[0]=='#include' and words[1]=='"modules/ExampleModule.h"':
                    for file in filesToAdd:
                        output.write('#include "modules/'+file+'.h"\n')
            if len(words)>=5:
                if words[0]=='#pragma' and words[1]=='link' and \
                   words[2]=='C++' and words[3]=='class' and \
                   words[4]=='ExampleModule+;':
                    for file in filesToAdd:
                        output.write('#pragma link C++ class '+file+'+;\n')

            output.write(line)

        input.close()
        output.close()

        try:
            shutil.copy(outputname,inputname)
        except:
            self.logger.error("impossible to copy "+outputname+' in '+inputname)
            return False

        return True

    def Deactivate(self):
        if self.main.archi_info.delphes_lib_paths==[]:
            return True
        for x in  self.main.archi_info.delphes_lib_paths:
            if 'DEACT' in x:
                return True
        if os.path.isdir(self.main.archi_info.delphes_lib_paths[0]):
            self.logger.warning("Delphes is installed. Deactivating it.")
            # Paths
            delpath=os.path.normpath(self.main.archi_info.delphes_lib_paths[0])
            deldeac = delpath.replace(delpath.split('/')[-1],"DEACT_"+delpath.split('/')[-1])
            self.main.archi_info.toLDPATH1 = [x for x in self.main.archi_info.toLDPATH1 if not 'delphes' in x]
            if 'Delphes' in self.main.archi_info.libraries.keys():
                del self.main.archi_info.libraries['Delphes']
            # If the deactivated directory already exists -> suppression
            if os.path.isdir(os.path.normpath(deldeac)):
                if not FolderWriter.RemoveDirectory(os.path.normpath(deldeac),True):
                        return False
            # cleaning delphes + the samplanalyzer interface to delphes
            shutil.move(delpath,deldeac)
            myexts = ['so', 'a', 'dylib']
            for ext in myexts:
                myfile=self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/Lib/libdelphes_for_ma5.'+ext
                if os.path.isfile(os.path.normpath(myfile)):
                    os.remove(os.path.normpath(myfile))

            ToRemove=[ 'Makefile_delphes','compilation_delphes.log','linking_delphes.log','cleanup_delphes.log']
            for myfile in ToRemove:
                if os.path.isfile(os.path.normpath(self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/Interfaces/'+myfile)):
                    os.remove(os.path.normpath(self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/Interfaces/'+myfile))
            self.main.archi_info.has_delphes = False
            self.main.archi_info.delphes_priority = False
            self.main.archi_info.delphes_lib_paths = []
            self.main.archi_info.delphes_inc_paths = []
            self.main.archi_info.delphes_lib = ""
            self.main.archi_info.delphes_original_libs = []
        return True

    def Activate(self):
        # output =  1: activation successfull.
        # output =  0: nothing is done.
        # output = -1: error
        user_info = UserInfo()
        user_info.ReadUserOptions(self.main.archi_info.ma5dir+'/madanalysis/input/installation_options.dat')
        checker = ConfigChecker(self.main.archi_info, user_info, self.main.session_info, self.main.script, False)
        hasdelphes = checker.checkDelphes(True)
        if hasdelphes:
            # Paths
            delpath=os.path.normpath(self.main.archi_info.delphes_lib_paths[0])
            deldeac = delpath.replace("DEACT_","")
            self.main.archi_info.delphes_lib=self.main.archi_info.delphes_lib.replace("DEACT_","")
            self.main.archi_info.delphes_original_libs =\
               [x.replace("DEACT_","") for x in self.main.archi_info.delphes_original_libs]
            self.main.archi_info.delphes_inc_paths =\
                [ x.replace("DEACT_","") for x in self.main.archi_info.delphes_inc_paths ]
            if len(self.main.archi_info.delphes_inc_paths)>2:
                del self.main.archi_info.delphes_inc_paths[-1]
                del self.main.archi_info.delphes_inc_paths[-1]
            self.main.archi_info.delphes_lib_paths =\
                list(set([ x.replace("DEACT_","") for x in self.main.archi_info.delphes_lib_paths ]))
            # do we have to activate delphes?
            if not 'DEACT' in delpath:
                return 0
            self.logger.warning("Delphes is deactivated. Activating it.")

            # naming
            shutil.move(delpath,deldeac)

            # Compiler setup
            compiler = LibraryWriter('lib',self.main)
            ncores = compiler.get_ncores2()

            from madanalysis.build.setup_writer import SetupWriter
            SetupWriter.WriteSetupFile(True,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/',self.main.archi_info)
            SetupWriter.WriteSetupFile(False,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/',self.main.archi_info)

#             if ncores>1:
#                 strcores='-j'+str(ncores)
            ToBuild =  ['delphes', 'root', 'process']

            # Makefile
            self.main.archi_info.has_delphes=True
            self.main.archi_info.delphes_priority=True
            dpath =  os.path.normpath(os.path.join(self.main.archi_info.ma5dir,'tools','delphes'))
            mylib = os.path.normpath(os.path.join(dpath,'libDelphes.so'))
            self.main.archi_info.libraries['Delphes']= mylib+":"+str(os.stat(mylib).st_mtime)
            self.main.archi_info.toLDPATH1 = [x for x in self.main.archi_info.toLDPATH1 if not 'MA5tune' in x]
            self.main.archi_info.toLDPATH1.append(dpath)

            for mypackage in ToBuild:
                if not compiler.WriteMakefileForInterfaces(mypackage):
                    self.logger.error("library building aborted.")
                    return -1

            # Cleaning
            for mypackage in ToBuild:
                myfolder='Process'
                if mypackage != 'process':
                    myfolder='Interfaces'
                if not compiler.MrProper(mypackage,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/'+myfolder):
                    self.logger.error("Library '" + mypackage + "' precleaning aborted.")
                    return -1

            # Compiling
            for mypackage in ToBuild:
                myfolder='Process'
                if mypackage != 'process':
                    myfolder='Interfaces'
                if not compiler.Compile(ncores,mypackage,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/'+myfolder):
                    self.logger.error("Library '" + mypackage + "' compilation aborted.")
                    return -1

            # Linking
            for mypackage in ToBuild:
                myfolder='Process'
                if mypackage != 'process':
                    myfolder='Interfaces'
                if not compiler.Link(mypackage,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/'+myfolder):
                    self.logger.error("Library '" + mypackage + "' linking aborted.")
                    return -1

            # Checking
            for mypackage in ToBuild:
                if mypackage == 'process':
                    myfolder='Lib/libprocess_for_ma5.so'
                elif mypackage == 'root':
                    myfolder='Lib/libroot_for_ma5.so'
                else:
                    myfolder='Lib/libdelphes_for_ma5.so'
                if not os.path.isfile(self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/'+myfolder):
                    self.logger.error("Library '" + mypackage + "' checking aborted.")
                    return -1

            # Cleaning
            for mypackage in ToBuild:
                myfolder='Process'
                if mypackage != 'process':
                    myfolder='Interfaces'
                if not compiler.Clean(mypackage,self.main.archi_info.ma5dir+'/tools/SampleAnalyzer/'+myfolder):
                    self.logger.error("Library '" + mypackage + "' cleaning aborted.")
                    return -1

            # Paths
            lev=self.logger.getEffectiveLevel()
            self.logger.setLevel(100)
            checkup = CheckUp(self.main.archi_info, self.main.session_info, False, self.main.script)
            if not checkup.SetFolder():
                self.logger.error("Problem with the path updates.")
                return -1

            if not self.main.archi_info.save(self.main.archi_info.ma5dir+'/tools/architecture.ma5'):
                return -1
            if not self.main.CheckConfig():
                return -1
            self.logger.setLevel(lev)

        return 1
