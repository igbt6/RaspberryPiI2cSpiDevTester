from PySide import QtCore, QtGui
from registersViewUi import Ui_RegistersView
from sshconnection import SshConnection
from threading import Thread
from time import sleep
import sys
import re
import ast

D=True #debug enabled

#C:\Python34\Scripts\pyside-uic.exe uiRegistersView.ui -o registersViewUi.py

class RegistersViewer(QtGui.QWidget):

    def __init__(self,  sshClient,deviceAddress,deviceName,regs,parent=None):
        self.deviceAddress = deviceAddress
        self.deviceName = deviceName
        self.registerList= regs
        self.sshClient=sshClient 
        super(RegistersViewer, self).__init__(parent)
        
        self.ui =  Ui_RegistersView()
        self.ui.setupUi(self)
        self.registersList= list()  
        self.formulasList = list()
        
        self.ui.RegistersTable.setColumnWidth(0,35)
        self.ui.RegistersTable.setColumnWidth(1,120)
        self.ui.RegistersTable.setColumnWidth(2,80)
        self.ui.RegistersTable.horizontalHeader().setStretchLastSection(True)
        self.ui.RegistersTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.ui.RegistersTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
 
        self.ui.bitmaskTableWidget.setColumnWidth(0,80)
        self.ui.bitmaskTableWidget.setColumnWidth(1,35)
        self.ui.bitmaskTableWidget.setColumnWidth(2,35)
        self.ui.bitmaskTableWidget.horizontalHeader().setStretchLastSection(True)
        self.ui.bitmaskTableWidget.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.ui.bitmaskTableWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        
        self.initConnections()
        
        self.maxRegisterNumber=0
        self.minRegisterNumber=9999
        self.loadRegisters()
        self.registerBitmaskEdited=-1;
        
        update_thread = Thread(target=self.RPiReadRegisters) 
        update_thread.daemon = True
        update_thread.start()
        
    def initConnections(self):			# setup all connections of signal and slots
        self.ui.AddFormulaButton.clicked.connect(self.addFormulaClicked);
        self.ui.RegistersTable.cellClicked.connect(self.reloadBitmaskWindow)
        self.ui.updateCommandLinkButton.clicked.connect(self.updateBitmaskOfGivenRegister) #TODO
    
    def addNewRegister(self,regNumber, name, value, function):
        self.ui.RegistersTable.insertRow(self.ui.RegistersTable.rowCount());
        
        #regTuple=(QtGui.QTableWidgetItem((regNumber)),QtGui.QTableWidgetItem(("%s" % name)),QtGui.QTableWidgetItem(( "0x%02x" % value)),QtGui.QTableWidgetItem(("%s" % function)));
        #self.registersList.append(regTuple);
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,0,QtGui.QTableWidgetItem((regNumber)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,1,QtGui.QTableWidgetItem(("%s" % name)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,2,QtGui.QTableWidgetItem(("0x%02x" % value)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,3,QtGui.QTableWidgetItem(("%s" % function)));
        
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,0,QtGui.QTableWidgetItem((regNumber)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,1,QtGui.QTableWidgetItem(("%s" % name)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,2,QtGui.QTableWidgetItem(("0x%02x" % value)));
        self.ui.RegistersTable.setItem(self.ui.RegistersTable.rowCount()-1,3,QtGui.QTableWidgetItem(("%s" % function)));
        
        if int(regNumber,16)<self.minRegisterNumber:
            self.minRegisterNumber=int(regNumber,16);
        if int(regNumber,16)>self.maxRegisterNumber:
            self.maxRegisterNumber=int(regNumber,16);
        
        #TODO add protection befor adding the same register number or name twice.
    
    def loadRegisters(self):
        if self.registerList is None:
            return
        for i in range(len(self.registerList)):
            self.addNewRegister(self.registerList[i][1],self.registerList[i][0],i,'none')
        self.ui.devNameLabel.setText(self.deviceName)
        self.ui.devAddrLabel.setText(self.deviceAddress)
    def reloadBitmaskWindow(self,row,column):
        if D:
            print("Row Nr %d" % row , "has been clicked")
        nrOfRows= self.ui.bitmaskTableWidget.rowCount()-1
        while(nrOfRows>-1):
            self.ui.bitmaskTableWidget.removeRow(nrOfRows)
            nrOfRows=nrOfRows-1
        
        self.registerBitmaskEdited = int(self.registerList[row][1],16);
        registerValue = self.getRegisterValue(int(self.registerList[row][1],16));
        
        for i in range(len(self.registerList[row][2])):
            mask = int(self.registerList[row][2][i]['Value'],16);
            maskValue=0;
            maskBitCounter=1;
            for i_bit in range (0,8):
                if (mask & (1<<i_bit))>0:
                    maskValue = maskValue + ((registerValue & (1<<i_bit))>0)*maskBitCounter;
                    maskBitCounter=maskBitCounter*2;
            
            self.ui.bitmaskTableWidget.insertRow(self.ui.bitmaskTableWidget.rowCount())
            self.ui.bitmaskTableWidget.setItem(self.ui.bitmaskTableWidget.rowCount()-1,0,QtGui.QTableWidgetItem(self.registerList[row][2][i]['Name']))
            self.ui.bitmaskTableWidget.setItem(self.ui.bitmaskTableWidget.rowCount()-1,1,QtGui.QTableWidgetItem(self.registerList[row][2][i]['Value']))
            self.ui.bitmaskTableWidget.setItem(self.ui.bitmaskTableWidget.rowCount()-1,2,QtGui.QTableWidgetItem(self.registerList[row][2][i]['Attr']))
            self.ui.bitmaskTableWidget.setItem(self.ui.bitmaskTableWidget.rowCount()-1,3,QtGui.QTableWidgetItem("%d" % maskValue))
        
    
    
    
    def updateRegisterValue(self,regNumber,value):
        for i in range(0,self.ui.RegistersTable.rowCount()):    #look for register with "number"
            if(self.ui.RegistersTable.item(i,0).text())==("0x%02x" % regNumber):      #check number match
                self.ui.RegistersTable.setItem(i,2,QtGui.QTableWidgetItem(("0x%02x" % value)));
                break;
    
    def getRegisterValue(self,regNumber):
        for i in range(0,self.ui.RegistersTable.rowCount()):        #look for register with "number"
           if (self.ui.RegistersTable.item(i,0).text())==("0x%02x" % regNumber):		#check number match
                return int(self.ui.RegistersTable.item(i,2).text(),16);
        return 0;
    
    def RPiReadRegisters(self):
        while 1:
            startIndex=self.minRegisterNumber;
            stopIndex=self.maxRegisterNumber+1;
            
            command = "python i2c_program/i2c_com.py read_block "+("0x%02x" % int(self.deviceAddress,16))+" "+("%d" % startIndex)+" "+("%d" % stopIndex);
            if D:
                print("Rpi command: "+command);
            response = self.sshClient.executeCommand(command,True)
            readValues=[];
            for line in response['STDOUT']:
                readValues = ast.literal_eval(line.strip('\n'))
            for i_reg in range(0,stopIndex-startIndex):
                self.updateRegisterValue(i_reg+startIndex,readValues[i_reg]);
            #sleep(0.2);
    
            self.updateFormulas();

    def RpiSetRegister(self,reg,value):
        command = "python i2c_program/i2c_com.py set_reg "+("0x%02x" % int(self.deviceAddress,16))+" "+("0x%02x"  % reg)+" "+("0x%02x" % value);
        if D:
            print("Rpi command: "+command);
        response = self.sshClient.executeCommand(command,True);
        for line in response['STDOUT']:
            RpiResponse = ast.literal_eval(line.strip('\n'))
            print ("Rpi response: "+RpiResponse);
        #sleep(0.2);

			
    def updateBitmaskOfGivenRegister(self):
        registerValue=0;
        for i in range(0,self.ui.bitmaskTableWidget.rowCount()):
            valueBit=0;
            mask=int(self.ui.bitmaskTableWidget.item(i,1).text(),16);
            bitmaskValue=int(self.ui.bitmaskTableWidget.item(i,3).text(),16);
            if bitmaskValue>mask:
                bitmaskValue=mask;
            for i_bit in range(0,8):
                if (mask & (1<<i_bit))>0:
                #    if(bitmaskValue&(1<<valueBit))>0:
                #        registerValue=registerValue+(1<<i_bit);
                #    valueBit=valueBit+1;
                    registerValue=registerValue+(bitmaskValue<<i_bit);
                    break;
        if D:
            print ("Register new value = "+("%d"%registerValue));
        print(self.registerBitmaskEdited);
        self.RpiSetRegister(int(self.registerBitmaskEdited),int(registerValue));
            
    def addFormulaClicked(self):
        print ("AddFormula()");
        formulaText = self.ui.FormulaText.toPlainText();
        
        reFormName = re.compile('\[(.*?)\]');
        reFormNameResult = reFormName.search(formulaText);
        if reFormNameResult:
            name=(reFormNameResult.group(0))[1:-1];
        else:
            return;
        
        formulaEval = formulaText.replace("["+name+"]","");
        print (formulaEval);
        self.addFormula(name,formulaEval);
    
    def addFormula(self,name,formula):
    
        formulaEval = formula;
        
        self.ui.FormulasTable.insertRow(self.ui.FormulasTable.rowCount());
        
        value=0;
        formulaTuple=(QtGui.QTableWidgetItem(("%s" % name)),QtGui.QTableWidgetItem(("0")), QtGui.QTableWidgetItem(("%s" % formulaEval)));
        self.formulasList.append(formulaTuple);
        
        self.ui.FormulasTable.setItem(self.ui.FormulasTable.rowCount()-1,0,self.formulasList[-1][0]);
        self.ui.FormulasTable.setItem(self.ui.FormulasTable.rowCount()-1,1,self.formulasList[-1][1]);
        self.ui.FormulasTable.setItem(self.ui.FormulasTable.rowCount()-1,2,self.formulasList[-1][2]);
        
    
    def setFormulaValue(self,number,value):
        self.ui.FormulasTable.setItem(number,1,QtGui.QTableWidgetItem(("%s" % value)));
    
    def updateFormulas(self):
        for i in range(0,len(self.formulasList)):
            evalCommand = self.formulasList[i][2].text();
            reFindR = re.compile('[r][0-9]+');
            reFindRResult = reFindR.findall(evalCommand);
            if reFindRResult:
                for ii in range(0,len(reFindRResult)):
                    regNumber = int((re.findall('\d+',reFindRResult[ii]))[0]);
                    evalCommand = evalCommand.replace(reFindRResult[ii],'self.getRegisterValue('+("%s"%regNumber)+')');
            evalRet=(eval(evalCommand));
            self.setFormulaValue(i,evalRet);

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    
    
    sshClient=SshConnection('172.16.1.102','pi', 'raspberry');
    sshClient.connect();
    
    myDeviceRegisters = RegistersViewer(sshClient,0x4D,'ADXL345',None);
    myDeviceRegisters.show();
    
    myDeviceRegisters.addNewRegister(0,"DataH",0x12,"ADC high value");
    myDeviceRegisters.addNewRegister(1,"DataL",0x10,"ADC low value");
    #myDeviceRegisters.addNewRegister(3,"Reg3",0x10,"This register doesnt do anything");
    
    myDeviceRegisters.addFormula("ADC data"," r0*256+r1");
    
    update_thread = Thread(target=myDeviceRegisters.RPiReadRegisters) 
    update_thread.daemon = True
    update_thread.start()
    

    sys.exit(app.exec_())
    
    
    



    