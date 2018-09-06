#!/usr/bin/python
'''
Copyright (c) 2012 Rowan Wookey <admin@rwky.net>
          (c) 2013 Bernd Schubert <bernd.schubert@itwm.fraunhofer.de>

           
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sys, subprocess, getopt

gitLogCmd = ['git','log','--pretty=oneline','--no-merges']
gitAuthorCmd = ['git', 'show', '-s', '--format=(%an) %aD']
gitCommitMsgCmd = ['git', 'log', '-1', '--pretty=%B']
gitFilterCmd  = ['git', 'show', '--pretty=medium', '--name-only']

branchAOnly  = False
branchBOnly  = False
reversedOrder = False

filterString  = ""
path = ""

changeIdLine = 'Change-Id:'

# just a basic commit object
class gitCommit:
    def __init__(self, commitID, commitSubject):
        self.commitID      = commitID
        self.commitSubject = commitSubject
        self.changeID  = ""

    def getCommitID(self):
        return self.commitID

    def getCommitSubject(self):
        return self.commitSubject

    def addChangeID(self, ID):
        self.changeID = ID

    def getChangeID(self):
        return self.changeID


class Branch:
    def __init__(self, branchName):
        self.branchName = branchName
        self.patchIdDict = {} # for fast search
        self.commitList = []  # list of gitCommit objects
        self.commitObjDict  = {}  # list of gitCommit objects
        self.missingList = [] # list of missing commitIDs of this branch

    def parserMsgData(self, commitID, commitObj):
        commitMsg = subprocess.check_output(gitCommitMsgCmd + [commitID])
        #print "commitMsg: " + commitMsg
        searchRegEx  = re.compile(cherryPickLine)
        searchRegEx1  = re.compile(changeIdLine)

        for line in commitMsg.splitlines():
            if searchRegEx.search(line):
                cherryPickID = searchRegEx.split(line)[1]
                #print "cherryPickID: " + cherryPickID
                # remove closing bracket
                cherryPickID = re.sub('\)$', '', cherryPickID)
                commitObj.addCherryPickID(cherryPickID)

            if searchRegEx1.search(line):
                changeID = searchRegEx.split(line)[0]
                # remove Change-Id:
                changeID = re.sub('Change-Id: ', '', changeID)
                commitObj.addChangeID(changeID)
                #print "changeID: " + changeID

    def addCommit(self, commitID, commitSubject):
        commitObj = gitCommit(commitID, commitSubject)

        # we don't use "git show", as it includes the message 
        diff = subprocess.check_output(['git', 'show', commitID])
        proc = subprocess.Popen(['git', 'patch-id'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        patchID = proc.communicate(input=diff)[0].split(' ')[0]

        self.parserMsgData(commitID,commitObj)

        # print self.branchName + ': Adding: ' + patchID + ' : ' + commitID
        self.commitList.append(commitID)
        self.commitObjDict[commitID] = commitObj
        self.commitObjDict[commitObj.getChangeID()] = commitObj
        self.patchIdDict[patchID] = commitID
        #print self.branchName + ': Adding: patchID ' + patchID + ' : commitID ' + commitID + ': Change-ID ' + commitObj.getChangeID()
 
    def addLogLine(self, logLine):
        commitID      = logLine[:40]
        commitSubject = logLine[41:]
        self.addCommit(commitID, commitSubject)

    def addGitLog(self, logOutput):
        lines = logOutput.split('\n')
        if lines[-1] == '':
            lines.pop()

        for line in lines:
            self.addLogLine(line)
    
    def doComparedBranchLog(self):
        cmd = gitLogCmd + [self.branchName]
        if 'since' in globals():
            cmd.append('--since="%s"' % since)
        # print 'Compared branch log: ' + str(cmd)

        log = subprocess.check_output(cmd );
        
        self.addGitLog(log)

    def createMissingList(self, comparisonDict):
        for key in comparisonDict.keys():
            if key not in self.patchIdDict:
                commitID = comparisonDict.get(key)
                self.missingList.append(commitID)

                # print self.branchName + ': missing: ' + key + ' : ' + commitID

    def isCommitInMissingList(self, commitID):
        if commitID in self.missingList:
            return True

        return False

    def printMissingCommits(self, comparisonCommitList):

        # Note: Print in the order given by the commitList and not
        #       in arbitrary order of the commit dictionary.

        print "Missing from %s" % self.branchName

        for commitObj in comparisonCommitList:
            commitID = commitObj.getCommitID()
            if self.isCommitInMissingList(commitID):
                cmd = gitAuthorCmd + [commitID]
                commitAuthor = subprocess.check_output(cmd).rstrip()

                print '  %s %s %s' % (commitID, commitAuthor, commitObj.getCommitSubject() )

        print


    def getPatchIdDict(self):
        return self.patchIdDict

    def getCommitList(self):
        return self.commitList

def usage():
        print '''
        Usage:

          -h 
                Print this help message.
          -a <branch-name> 
                The name of branch a.
          -b <branch-name> 
                The name of branch b.
          -A 
                List all commits in branch b but doesn't present in branch a.
          -B 
                 List all commits in branch a but doesn't present in branch b.
          -r
                Print in reverse order (older (top) to newer (bottom) )
          -t
                How far back in time to go (passed to git log as --since) i.e. '1 month ago'
          -p
                Specific path or file
          -F
                Specifi a filter, the filter will check changed file name and commit comments

        '''


try:
    opts, args = getopt.getopt(sys.argv[1:], "ha:b:BArt:F:p:")
except:
    usage()
    sys.exit()
    

for opt,arg in opts:
    if opt == '-h':
        usage()   
        sys.exit();
    if opt == '-a':
        branchAName = arg
    if opt == '-b':
        branchBName = arg
    if opt == '-A':
        branchAOnly = True
    if opt == '-B':
        branchBOnly = True
    if opt == '-r':
        reversedOrder = True
    if opt == '-t':
        since = arg
    if opt == '-F':
        filterString = arg
        print "include file:"+filterString
    if opt == '-p':
        path = arg
        print "PATH:"+path


if 'branchAName' not in globals() or 'branchBName' not in globals():
    print 'You must specify two branches with -a and -b'
    sys.exit(1)

if reversedOrder:
    gitLogCmd += ['--reverse']


branchAObj = Branch(branchAName)
branchBObj = Branch(branchBName)


branchAObj.doComparedBranchLog()
branchBObj.doComparedBranchLog()

branchAObj.createMissingList(branchBObj.getPatchIdDict() )
branchBObj.createMissingList(branchAObj.getPatchIdDict() )


#print

if not branchBOnly:
    branchAObj.printMissingCommits(branchBObj.getCommitList() )

if not branchAOnly:
    branchBObj.printMissingCommits(branchAObj.getCommitList() )

#if not branchBOnly and not branchAOnly:
#    print
#    print "Commits that can be probably ignored due to merge conflicts: "
#    for msg in branch1_commit_msg:
#        if msg in branch2_commit_msg:
#            print '  ' + msg


