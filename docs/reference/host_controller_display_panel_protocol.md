# Host Controller and Display Panel Communication Protocol

## 1 Introduction
The energy storage inverter controller consists of a master controller, a slave controller, and a display panel controller. 
* **Master Controller:** Mainly responsible for the grid-connected algorithm voltage outer loop, the Bus voltage regulation control loop, MPPT, related grid interface algorithms, power and electricity statistics, and system protection functions.
* **Slave Controller:** Mainly responsible for DC-DCDC conversion, DC boost, master-slave consistency detection, etc.
* **Display Board Controller:** Mainly responsible for the display of system work information.

Therefore, it is necessary to define the communication protocol between the main controller and the display board.

---

## 2 Definition of Communication Interface
The main controller and the display board use UART communication with the following settings:
* **Baud Rate:** 115200 bps
* **Data Bits:** 8 bits
* **Stop Bits:** 1 bit
* **Parity Check:** None
* **Flow Control:** None
* **Communication Mode:** Half-duplex communication mode. At any given time, only one of the master and the slave can send data while the other receives. 

Communication between the main controller and the display panel is initiated by the display panel, and the main controller responds (does not initiate communication actively). The communication frame is based on the MODBUS protocol frame.

---

## 3 Communication Frame Definition

### Frame Structure
| Field | Value / Description |
| :--- | :--- |
| **Frame Header** | 0xAA 0xAA |
| **Slave Address Field** | 0-247 (decimal) (0 is broadcast address) |
| **Functional Domain** | `0x03`: read multiple parameters<br>`0x06`: write a single parameter<br>`0x10`: write multiple parameters<br>`0x17`: Master-slave synchronization data<br>`0x41`: Firmware upgrade |
| **Data Field** | Includes the register address field and the data payload field |
| **CRC Field** | 16-bit CRC check value |
| **End of Frame** | 0x55 0x55 |

#### Example Register Mapping Reference
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 001DH | 1 | PV1Volt | UInt16 | 0.1 | V | R | PV1 voltage |

*Note: When PV1 voltage is 300.5V, the Register address PV1Volt’s value is 3005.*

### 3.1 Communication Frame Command and Frame Description
The CRC check range spans from the slave address field to the data field (excluding the frame header and the CRC field itself). The frame header does not need to be included when calculating the CRC check.

#### 3.1.1 0x03 Read Multiple Registers
This function code (command) is used to read the contents of a continuous block of registers. The request protocol data unit specifies the starting register address and the number of registers.

In the response register data, each register data contains two bytes (binary numbers are right-justified in each byte). For each register, the first byte is high and the second byte is low.

**Example: Request to read register 0x0001 - 0x0002**

| Request Field | Hex Value | | Answer Field | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **Frame Header** | AA AA | | **Frame Header** | AA AA |
| **Slave Address** | 0A | | **Slave Address** | 0A |
| **Command** | 03 | | **Command** | 03 |
| **Register Start Address High Order** | 00 | | **Number of Bytes** | 04 |
| **Register Start Address Low Order** | 01 | | **Register Value High (01)** | 0F |
| **Register Number High Bit** | 00 | | **Register Value Low (01)** | A0 |
| **Register Count Low** | 02 | | **Register Value High (02)** | 01 |
| **CRC Low** | *---* | | **Register Value Low (02)** | C2 |
| **CRC High** | *---* | | **CRC Low** | *---* |
| **End of Frame** | 55 55 | | **CRC High** | *---* |
| | | | **End of Frame** | 55 55 |

---

#### 3.1.2 0x06 Write a Single Register
This function code (command) is used to write to a single holding register in the slave device. The request specifies the address of the register to be written. The normal response is an exact echo of the request, returning the value that was written.

**Example: Write the value 0xAAAA to register address 0x0008**

| Request Field | Hex Value | | Answer Field | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **Frame Header** | AA AA | | **Frame Header** | AA AA |
| **Slave Address** | 0A | | **Slave Address** | 0A |
| **Request** | 06 | | **Answer** | 06 |
| **Register Start Address High Order** | 00 | | **Register Start Address High Order** | 00 |
| **Register Start Address Low Order** | 08 | | **Register Start Address Low Order** | 08 |
| **Register Value High** | AA | | **Register Value High** | AA |
| **Register Value Low** | AA | | **Register Value Low** | AA |
| **CRC Low** | *---* | | **CRC Low** | *---* |
| **CRC High** | *---* | | **CRC High** | *---* |
| **End of Frame** | 55 55 | | **End of Frame** | 55 55 |

---

#### 3.1.3 0x10 Write Multiple Registers
This function code (command) is used to write a block (string) of consecutive addresses to the registers. The values to be written are specified in the data field. Each register is a two-byte word. A normal response returns the function code, start address, and the total number of registers written.

**Example: Write data 0x1194 to register 0x0001, and data 0x01CC to register 0x0002**

| Request Field | Hex Value | | Answer Field | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **Frame Header** | AA AA | | **Frame Header** | AA AA |
| **Slave Address** | 0A | | **Slave Address** | 0A |
| **Request** | 10 | | **Request** | 10 |
| **Register Start Address High Order** | 00 | | **Register Start Address High Order** | 00 |
| **Register Start Address Low Order** | 01 | | **Register Start Address Low Order** | 01 |
| **Register Count High** | 00 | | **Register Count High** | 00 |
| **Register Count Low** | 02 | | **Register Count Low** | 02 |
| **Number of Bytes** | 04 | | **CRC Low** | *---* |
| **Register Value High (01)** | 11 | | **CRC High** | *---* |
| **Register Value Low (01)** | 94 | | **End of Frame** | 55 55 |
| **Register Value High (02)** | 01 | | | |
| **Register Value Low (02)** | CC | | | |
| **CRC Low** | *---* | | | |
| **CRC High** | *---* | | | |
| **End of Frame** | 55 55 | | | |

---

#### 3.1.4 0x17 Read/Write Multiple Registers (Master-Slave Synchronous Data)
This function code (command) performs one read operation and one write operation simultaneously in a single data transfer, allowing high-efficiency synchronous multiple data reading and writing.

**Example Configuration Transfer:**

| Request Field | Hex Value | | Answer Field | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **Frame Header** | AA AA | | **Frame Header** | AA AA |
| **Slave Address** | 11 | | **Slave Address** | 11 |
| **Command** | 17 | | **Command** | 17 |
| **Read Register Start Address High Order**| 00 | | **Number of Bytes** | 0C |
| **Read Register Start Address Low Order** | 04 | | **Register Value High (04)** | 00 |
| **Read High Order of Number of Registers**| 00 | | **Register Value Low (04)** | FE |
| **Read Low Order of Number of Registers** | 06 | | **Register Value High (05)** | 0A |
| **Write Register Start Address High Order**| 00 | | **Register Value Low (05)** | CD |
| **Write Register Start Address Low Order** | 0F | | **Register Value High (06)** | 00 |
| **Write Register Number High Bit** | 00 | | **Register Value Low (06)** | 01 |
| **Write Register Count Low** | 03 | | **Register Value High (07)** | 00 |
| **Number of Bytes** | 06 | | **Register Value Low (07)** | 03 |
| **Write Register Value High (0F)** | 00 | | **Register Value High (08)** | 00 |
| **Write Register Value Low (0F)** | FF | | **Register Value Low (08)** | 0D |
| **Write Register Value High (10)** | 00 | | **Register Value High (09)** | 00 |
| **Write Register Value Low (10)** | FF | | **Register Value Low (09)** | FF |
| **Write Register Value High (11)** | 00 | | **CRC Low** | *---* |
| **Write Register Value Low (11)** | FF | | **CRC High** | *---* |
| **CRC Low** | *---* | | **End of Frame** | 55 55 |
| **CRC High** | *---* | | | |
| **End of Frame** | 55 55 | | | |

---

#### 3.1.5 Error Response Frame Definition
Once the slave (server) receives a request, there are two types of responses depending on the processing result:
1. **Normal Response:** The response function code mirrors the request function code.
2. **Abnormal Response:** The server sets the highest position bit of the function code to 1 (Function Code + 0x80) and appends an exception code.

##### Exception Codes
| Error Code (Hex) | Description |
| :---: | :--- |
| **01** | Illegal function code |
| **02** | Invalid request address |
| **03** | Illegal request data value |
| **04** | Server failure |
| **06** | Server is busy |
| **10** | Wrong password |
| **11** | Check error |
| **12** | Invalid argument |
| **13** | System locked |

**Example: Master reads data, and the slave responds abnormally**

| Request Field | Hex Value | | Response Field | Hex Value |
| :--- | :--- | :--- | :--- | :--- |
| **Frame Header** | AA AA | | **Frame Header** | AA AA |
| **Slave Address** | 0A | | **Slave Address** | 0A |
| **Command** | 03 | | **Command** | 83 |
| **Register Start Address High Order** | 00 | | **Error Code** | 02 |
| **Register Start Address Low Order** | 01 | | **CRC Low** | *---* |
| **Register Number High Bit** | 00 | | **CRC High** | *---* |
| **Register Count Low** | 02 | | **End of Frame** | 55 55 |
| **CRC Low** | *---* | | | |
| **CRC High** | *---* | | | |
| **End of Frame** | 55 55 | | | |

---

## 4 Inverter Data Register Definition

### 4.1 Information Register Definition
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description | Remark |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| 8F00H | 1 | Type | UInt16 | 0 | | R | DeviceType | 0x0052: Single-phase AC coupling integrated machine AS1 series |
| 8F01H | 1 | SubType | UInt16 | | | R | Subclass | |
| 8F02H | 1 | CommProVersion | UInt16 | -3 | | R | Comms Protocol Version | |
| 8F03H | 10 | SN | String(20) | | | R | SerialNumber | Invalid value: 0x00 |
| 8F0DH | 10 | PC | String(20) | | | R | ProductCode | Invalid value: 0x00 |
| 8F17H | 1 | DV | UInt16 | -3 | | R | Display Software Version | Invalid value: 0xFFFF |
| 8F18H | 1 | MCV | UInt16 | -3 | | R | Master Ctrl Software Version | Invalid value: 0xFFFF |
| 8F19H | 1 | SCV | UInt16 | -3 | | R | Slave Ctrl Software Version | Invalid value: 0xFFFF |
| 8F1AH | 1 | DispHWVersion | UInt16 | -3 | | R | DispBoardHardware Version | Invalid value: 0xFFFF |
| 8F1BH | 1 | CtrlHWVersion | UInt16 | -3 | | R | CtrlBoardHardware Version | Invalid value: 0xFFFF |
| 8F1CH | 1 | PowerHWVersion | UInt16 | -3 | | R | PowerBoardHardware Version | Invalid value: 0xFFFF |
| 8F1DH | 1 | BatNum | UInt16 | 0 | | R | Number of batteries | Unused |
| 8F1EH | 10 | CCID | String(20) | | | R | GPRS CCID | Invalid value: 0x00 |
| 8F28H | 10 | SN_MOD | String(20) | | | R | SerialNumber | Invalid value: 0x00 |
| 8F32H | 10 | PC_MOD | String(20) | | | R | ProductCode | Invalid value: 0x00 |
| 8F3CH | 1 | MOD_Version | UInt16 | -3 | | R | Module software version | Invalid value: 0xFFFF |
| 8F3DH | 1 | MOD_HWVersion | UInt16 | -3 | | R | Module Hardware Version | Invalid value: 0xFFFF |
| 8F3EH | 16 | ServerIP | String(32) | | | R | Server domain name or IP | Can use domain name or IP as string type |
| 8F4EH | 1 | ServerPort | UInt16 | 0 | | R | Server port | |
| 8F4FH | 16 | Slave_ServerIP | String(32) | | | R | Server domain name or IP | Reserved |
| 8F5FH | 1 | Slave_ServerPort| UInt16 | 0 | | R | Slave server port | Reserved |
| 8F60H | 1 | SIGNAL | UInt16 | 0 | | R | GPRS SIGNAL | Invalid Value: 0xFFFF |
| 8F61H | 10 | Operator | String(20) | 0 | | R | GPRS Operator | Reserve |
| 8F6BH | 10 | IMEI | String(20) | 0 | | R | GPRS IMEI | Invalid Value: 0x00 |
| 8F75H | 1 | BLE_FWVersion | UInt16 | -3 | | R | Bluetooth Firmware Version | Invalid Value: 0xFFFF |
| 8F76H | 1 | ReportWay | UInt16 | 0 | | R | Reporting Way | Invalid Value: 0xFFFF<br>0: No connection<br>1: 4G<br>2: Ethernet |

---

### 4.2 Peripheral Information Register Definition (Peripheral_Information 寄存器定义)
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| 8E00H | 1 | BMS1_type | UInt16 | | | R | BMS1 type |
| 8E01H | 8 | BMS1_SN | String(16) | | | R | BMS 1 SN |
| 8E09H | 1 | BMS1_software_Version | UInt16 | -3 | | R | BMS firmware version 1 |
| 8E0AH | 1 | BMS1_hardware_Version | UInt16 | -3 | | R | BMS hardware version 1 |
| 8E0BH | 1 | BAT1_type | UInt16 | | | R | Battery 1 type |
| 8E0CH | 8 | BAT1_SN | String(16) | | | R | Battery 1 SN |
| 8E14H | 1 | BMS2_type | UInt16 | | | R | BMS2 Type |
| 8E15H | 8 | BMS2_SN | String(16) | | | R | BMS 2 SN |
| 8E1DH | 1 | BMS2_software_Version | UInt16 | -3 | | R | BMS firmware version 2 |
| 8E1EH | 1 | BMS2_hardware_Version | UInt16 | -3 | | R | BMS hardware version 2 |
| 8E1FH | 1 | BAT2_type | UInt16 | | | R | Battery 2 type |
| 8E20H | 8 | BAT2_SN | String(16) | | | R | Battery 2 SN |
| 8E28H | 1 | BMS3_type | UInt16 | | | R | BMS3 type |
| 8E29H | 8 | BMS3_SN | String(16) | | | R | BMS 3 SN |
| 8E31H | 1 | BMS3_software_Version | UInt16 | -3 | | R | BMS firmware version 3 |
| 8E32H | 1 | BMS3_hardware_Version | UInt16 | -3 | | R | BMS hardware version 3 |
| 8E33H | 1 | BAT3_type | UInt16 | | | R | Battery 3 type |
| 8E34H | 8 | BAT3_SN | String(16) | | | R | Battery 3 SN |
| 8E3CH | 1 | BMS4_type | UInt16 | | | R | BMS4 type |
| 8E3DH | 8 | BMS4_SN | String(16) | | | R | BMS 4 SN |
| 8E45H | 1 | BMS4_software_Version | UInt16 | -3 | | R | BMS firmware version 4 |
| 8E46H | 1 | BMS4_hardware_Version | UInt16 | -3 | | R | BMS hardware version 4 |
| 8E47H | 1 | BAT4_type | UInt16 | | | R | Battery 4 type |
| 8E48H | 8 | BAT4_SN | String(16) | | | R | Battery 4 SN |

---

### 4.3 Realtime Data Register Definition
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| 4000H | 4 | Time | HEX | 0 | | R/W | Inverter current time |
| 4004H | 1 | MPVMode | UInt16 | | | R | Inverter working mode |
| 4005H | 2 | HFaultMSG | UInt32 | | | R | Display board error messages |
| 4007H | 2 | MFaultMSG | UInt32 | | | R | Primary controller error message |
| 4009H | 2 | MFaultMSG2 | UInt32 | | | R | Primary controller error message 2 |
| 400BH | 2 | SFaultMSG | UInt32 | | | R | Error message from controller |
| 400DH | 2 | SFaultMSG2 | UInt32 | | | R | Error message from controller 2 |
| 400FH | 1 | Error_Count | UInt16 | 0 | | R | Number of inverter error warning messages |
| 4010H | 1 | SinkTempC | Int16 | -1 | ℃ | R | Radiator temperature |
| 4016H | 1 | ISO4 | UInt16 | 0 | kΩ | R | PV__ISO |
| 4019H | 1 | ConnTime | UInt16 | 0 | S | R | Countdown to grid connection |
| 4031H | 1 | RGridVolt | UInt16 | -1 | V | R | R phase voltage |
| 4032H | 1 | RGridCurr | Int16 | -2 | A | R | R phase current |
| 4033H | 1 | RGridFreq | UInt16 | -2 | Hz | R | R phase frequency |
| 4034H | 1 | RGridDCI | Int16 | 0 | mA | R | R phase DC component of grid |
| 4035H | 1 | RGridPowerWatt | Int16 | 0 | W | R | R phase grid active power |
| 4036H | 1 | RGridPowerVA | UInt16 | 0 | W | R | R phase grid reactive power |
| 4037H | 1 | RGridPowerPF | Int16 | -3 | | R | R phase grid power factor |
| 4046H | 1 | RInvVolt | UInt16 | -1 | V | R | R phase Inversion voltage |
| 4047H | 1 | RInvCurr | Int16 | -2 | A | R | R phase Inversion current |
| 4048H | 1 | RInvFreq | UInt16 | -2 | Hz | R | R inv frequency |
| 4049H | 1 | RInvPowerWatt | Int16 | 0 | W | R | R inv active power |
| 404AH | 1 | RInvPowerVA | UInt16 | 0 | VA | R | R inv reactive power |
| 4055H | 1 | ROutVolt | UInt16 | -1 | V | R | R export voltage |
| 4056H | 1 | ROutCurr | UInt16 | -2 | A | R | R export current |
| 4057H | 1 | ROutFreq | UInt16 | -2 | Hz | R | R export frequency |
| 4058H | 1 | ROutDVI | Int16 | 0 | mV | R | R DC component of output voltage |
| 4059H | 1 | ROutPowerWatt | UInt16 | 0 | W | R | R output active power |
| 405AH | 1 | ROutPowerVA | UInt16 | 0 | VA | R | R output apparent power |
| 4067H | 1 | BusVoltMaster | UInt16 | -1 | V | R | Master BUS voltage |
| 4068H | 1 | BusVoltSlave | UInt16 | -1 | V | R | Slave BUS voltage |
| 4069H | 1 | BatVolt | UInt16 | -1 | V | R | Battery voltage |
| 406AH | 1 | BatCurr | Int16 | -2 | A | R | Battery current |
| 406DH | 1 | BatPower | Int16 | 0 | W | R | Battery power |
| 406EH | 1 | BatTempC | Int16 | -1 | ℃ | R | Battery temperature |
| 406FH | 1 | BatEnergyPercent| UInt16 | -2 | % | R | Battery SOC |
| 4095H | 1 | PV_direction | UInt16 | 0 | | R | PV direction of energy flow |
| 4096H | 1 | Battery_direction| Int16 | 0 | | R | Battery energy flow direction |
| 4097H | 1 | Grid_direction | Int16 | 0 | | R | Grid energy flow direction |
| 4098H | 1 | OutPut_direction| UInt16 | 0 | | R | Output to load energy flow direction |
| 4099H | 1 | PVConsumpWatt | Int16 | 0 | W | R | Power flow from PV to load |
| 409AH | 1 | GridConsumpWatt | Int16 | 0 | W | R | Power flowing from the grid to the load |
| 409BH | 1 | GridFeedInPVWatt| Int16 | 0 | W | R | Power flow from PV to grid |
| 409CH | 1 | GridFeedInBatWatt| Int16 | 0 | W | R | Power flow from battery to grid |
| 409DH | 1 | BatConsumpWatt | Int16 | 0 | W | R | Power flow from battery to load |
| 409EH | 1 | BatChgPVWatt | Int16 | 0 | W | R | PV charging power to battery |
| 409FH | 1 | BatChgGridWatt | Int16 | 0 | W | R | Grid charging power to battery |
| 40A0H | 1 | SysTotalLoadWatt| Int16 | 0 | W | R | Total system load power consumption |
| 40A1H | 1 | CT_GridPowerWatt| Int16 | 0 | W | R | CT grid active power |
| 40A2H | 1 | CT_GridPowerVA | Int16 | 0 | VA | R | CT grid apparent power |
| 40A3H | 1 | CT_PVPowerWatt | Int16 | 0 | W | R | CT PV active power |
| 40A4H | 1 | CT_PVPowerVA | Int16 | 0 | VA | R | CT PV apparent power |
| 40A5H | 1 | TotalPVPower | Int16 | 0 | W | R | PV total power |
| 40A6H | 1 | TotalBatteryPower| Int16 | 0 | W | R | Total battery power |
| 40A7H | 1 | TotalGridPowerWatt| Int16 | 0 | W | R | The total active power of the grid |
| 40A8H | 1 | TotalGridPowerVA| Int16 | 0 | VA | R | The total apparent power of the grid |
| 40A9H | 1 | TotalInvPowerWatt| Int16 | 0 | W | R | Inverter total active power |
| 40AAH | 1 | TotalInvPowerVA | Int16 | 0 | VA | R | Inverter total apparent power |
| 40ABH | 1 | BackupTotalLoadPowerWatt| UInt16| 0 | W | R | Backup Total load active power |
| 40ACH | 1 | BackupTotalLoadPowerVA| UInt16 | 0 | VA | R | Backup Total load apparent power |
| 40ADH | 1 | BatChgPowerLimit| Int16 | 0 | W | R | PV Charging power limit |
| 40BCH | 1 | Today_Hour | UInt16 | -1 | H | R | PV Grid-connected daily power generation time |
| 40BDH | 2 | Total_Hour | UInt32 | -1 | H | R | PV Grid-connected total power generation time |
| 40BFH | 2 | Today_PVEnergy | UInt32 | -2 | kWh | R | Daily PV power generation |
| 40C1H | 2 | Month_PVEnergy | UInt32 | -2 | kWh | R | Monthly PV power generation |
| 40C3H | 2 | Year_PVEnergy | UInt32 | -2 | kWh | R | Yearly PV power generation |
| 40C5H | 2 | Total_PVEnergy | UInt32 | -2 | kWh | R | Total PV power generation |
| 40C7H | 2 | Today_BatChgEnergy| UInt32 | -2 | kWh | R | Daily battery charge |
| 40C9H | 2 | Month_BatChgEnergy| UInt32 | -2 | kWh | R | Monthly battery charge |
| 40CBH | 2 | Year_BatChgEnergy| UInt32 | -2 | kWh | R | Annual battery charge |
| 40CDH | 2 | Total_BatChgEnergy| UInt32 | -2 | kWh | R | Total battery charge |
| 40CFH | 2 | Today_BatDisEnergy| UInt32 | -2 | kWh | R | Today_BatDisEnergy |
| 40D1H | 2 | Month_BatDisEnergy| UInt32 | -2 | kWh | R | Month_BatDisEnergy |
| 40D3H | 2 | Year_BatDisEnergy| UInt32 | -2 | kWh | R | Year_BatDisEnergy |
| 40D5H | 2 | Total_BatDisEnergy| UInt32 | -2 | kWh | R | Total_BatDisEnergy |
| 40D7H | 2 | Today_InvGenEnergy| UInt32 | -2 | kWh | R | Today_InvGenEnergy |
| 40D9H | 2 | Month_InvGenEnergy| UInt32 | -2 | kWh | R | Month_InvGenEnergy |
| 40DBH | 2 | Year_InvGenEnergy| UInt32 | -2 | kWh | R | Year_InvGenEnergy |
| 40DDH | 2 | Total_InvGenEnergy| UInt32 | -2 | kWh | R | Total_InvGenEnergy |
| 40DFH | 2 | Today_TotalLoadEnergy| UInt32 | -2 | kWh | R | Today_TotalLoadEnergy |
| 40E1H | 2 | Month_TotalLoadEnergy| UInt32 | -2 | kWh | R | Month_TotalLoadEnergy |
| 40E3H | 2 | Year_TotalLoadEnergy| UInt32 | -2 | kWh | R | Year_TotalLoadEnergy |
| 40E5H | 2 | Total_TotalLoadEnergy| UInt32 | -2 | kWh | R | Total_TotalLoadEnergy |
| 40E7H | 2 | Today_BackupLoadEnergy| UInt32| -2 | kWh | R | Today_BackupLoadEnergy |
| 40E9H | 2 | Month_BackupLoadEnergy| UInt32| -2 | kWh | R | Month_BackupLoadEnergy |
| 40EBH | 2 | Year_BackupLoadEnergy| UInt32 | -2 | kWh | R | Year_BackupLoadEnergy |
| 40EDH | 2 | Total_BackupLoadEnergy| UInt32| -2 | kWh | R | Total_BackupLoadEnergy |
| 40EFH | 2 | Today_SellEnergy| UInt32 | -2 | kWh | R | Today_SellEnergy |
| 40F1H | 2 | Month_SellEnergy| UInt32 | -2 | kWh | R | Month_SellEnergy |
| 40F3H | 2 | Year_SellEnergy | UInt32 | -2 | kWh | R | Year_SellEnergy |
| 40F5H | 2 | Total_SellEnergy| UInt32 | -2 | kWh | R | Total_SellEnergy |
| 40F7H | 2 | Today_FeedInEnergy| UInt32| -2 | kWh | R | Today_FeedInEnergy |
| 40F9H | 2 | Month_FeedInEnergy| UInt32| -2 | kWh | R | Month_FeedInEnergy |
| 40FBH | 2 | Year_FeedInEnergy| UInt32 | -2 | kWh | R | Year_FeedInEnergy |
| 40FDH | 2 | Total_FeedInEnergy| UInt32| -2 | kWh | R | Total_FeedInEnergy |
| 40FFH | 2 | Today_PVConsumpEnergy| UInt32| -2 | kWh | R | Today_PVConsumpEnergy |
| 4101H | 2 | Month_PVConsumpEnergy| UInt32| -2 | kWh | R | Month_PVConsumpEnergy |
| 4103H | 2 | Year_PVConsumpEnergy| UInt32 | -2 | kWh | R | Year_PVConsumpEnergy |
| 4105H | 2 | Total_PVConsumpEnergy| UInt32| -2 | kWh | R | Total_PVConsumpEnergy |
| 4107H | 2 | Today_GridConsumpEnergy| UInt32| -2 | kWh | R | Today_GridConsumpEnergy |
| 4109H | 2 | Month_GridConsumpEnergy| UInt32| -2 | kWh | R | Month_GridConsumpEnergy |
| 410BH | 2 | Year_GridConsumpEnergy| UInt32 | -2 | kWh | R | Year_GridConsumpEnergy |
| 410DH | 2 | Total_GridConsumpEnergy| UInt32| -2 | kWh | R | Total_GridConsumpEnergy |
| 410FH | 2 | Today_GridFeedInPVEnergy| UInt32| -2| kWh | R | Today_GridFeedInPVEnergy |
| 4111H | 2 | Month_GridFeedInPVEnergy| UInt32| -2| kWh | R | Month_GridFeedInPVEnergy |
| 4113H | 2 | Year_GridFeedInPVEnergy| UInt32 | -2 | kWh | R | Year_GridFeedInPVEnergy |
| 4115H | 2 | Total_GridFeedInPVEnergy| UInt32| -2| kWh | R | Total_GridFeedInPVEnergy |
| 4117H | 2 | Today_GridFeedInBatEnergy| UInt32| -2| kWh | R | Today_GridFeedInBatEnergy |
| 4119H | 2 | Month_GridFeedInBatEnergy| UInt32| -2| kWh | R | Month_GridFeedInBatEnergy |
| 411BH | 2 | Year_GridFeedInBatEnergy| UInt32 | -2 | kWh | R | Year_GridFeedInBatEnergy |
| 411DH | 2 | Total_GridFeedInBatEnergy| UInt32| -2| kWh | R | Total_GridFeedInBatEnergy |
| 411FH | 2 | Today_BatConsumpEnergy| UInt32 | -2 | kWh | R | Today_BatConsumpEnergy |
| 4121H | 2 | Month_BatConsumpEnergy| UInt32 | -2 | kWh | R | Month_BatConsumpEnergy |
| 4123H | 2 | Year_BatConsumpEnergy| UInt32  | -2 | kWh | R | Year_BatConsumpEnergy |
| 4125H | 2 | Total_BatConsumpEnergy| UInt32 | -2 | kWh | R | Total_BatConsumpEnergy |
| 4127H | 2 | Today_BatChgPVEnergy| UInt32   | -2 | kWh | R | Today_BatChgPVEnergy |
| 4129H | 2 | Month_BatChgPVEnergy| UInt32   | -2 | kWh | R | Month_BatChgPVEnergy |
| 412BH | 2 | Year_BatChgPVEnergy| UInt32    | -2 | kWh | R | Year_BatChgPVEnergy |
| 412DH | 2 | Total_BatChgPVEnergy| UInt32   | -2 | kWh | R | Total_BatChgPVEnergy |
| 412FH | 2 | Today_BatChgGridEnergy| UInt32 | -2 | kWh | R | Today_BatChgGridEnergy |
| 4131H | 2 | Month_BatChgGridEnergy| UInt32 | -2 | kWh | R | Month_BatChgGridEnergy |
| 4133H | 2 | Year_BatChgGridEnergy| UInt32  | -2 | kWh | R | Year_BatChgGridEnergy |
| 4135H | 2 | Total_BatChgGridEnergy| UInt32 | -2 | kWh | R | Total_BatChgGridEnergy |
| 4137H | 2 | Today_PVEnergy2 | UInt32       | -2 | kWh | R | Today_PVEnergy2 |
| 4139H | 2 | Month_PVEnergy2 | UInt32       | -2 | kWh | R | Month_PVEnergy2 |
| 413BH | 2 | Year_PVEnergy2 | UInt32        | -2 | kWh | R | Year_PVEnergy2 |
| 413DH | 2 | Total_PVEnergy2 | UInt32       | -2 | kWh | R | Total_PVEnergy2 |
| 413FH | 2 | Today_PVEnergy3 | UInt32       | -2 | kWh | R | Today_PVEnergy3 |
| 4141H | 2 | Month_PVEnergy3 | UInt32       | -2 | kWh | R | Month_PVEnergy3 |
| 4143H | 2 | Year_PVEnergy3 | UInt32        | -2 | kWh | R | Year_PVEnergy3 |
| 4145H | 2 | Total_PVEnergy3 | UInt32       | -2 | kWh | R | Total_PVEnergy3 |
| 4147H | 2 | Today_SellEnergy2 | UInt32     | -2 | kWh | R | Today_SellEnergy2 |
| 4149H | 2 | Month_SellEnergy2 | UInt32     | -2 | kWh | R | Month_SellEnergy2 |
| 414BH | 2 | Year_SellEnergy2 | UInt32      | -2 | kWh | R | Year_SellEnergy2 |
| 414DH | 2 | Total_SellEnergy2 | UInt32     | -2 | kWh | R | Total_SellEnergy2 |
| 414FH | 2 | Today_SellEnergy3 | UInt32     | -2 | kWh | R | Today_SellEnergy3 |
| 4151H | 2 | Month_SellEnergy3 | UInt32     | -2 | kWh | R | Month_SellEnergy3 |
| 4153H | 2 | Year_SellEnergy3 | UInt32      | -2 | kWh | R | Year_SellEnergy3 |
| 4155H | 2 | Total_SellEnergy3 | UInt32     | -2 | kWh | R | Total_SellEnergy3 |
| 4157H | 2 | Today_FeedInEnergy2| UInt32    | -2 | kWh | R | Today_FeedInEnergy2 |
| 4159H | 2 | Month_FeedInEnergy2| UInt32    | -2 | kWh | R | Month_FeedInEnergy2 |
| 415BH | 2 | Year_FeedInEnergy2| UInt32     | -2 | kWh | R | Year_FeedInEnergy2 |
| 415DH | 2 | Total_FeedInEnergy2| UInt32    | -2 | kWh | R | Total_FeedInEnergy2 |
| 415FH | 2 | Today_FeedInEnergy3| UInt32    | -2 | kWh | R | Today_FeedInEnergy3 |
| 4161H | 2 | Month_FeedInEnergy3| UInt32    | -2 | kWh | R | Month_FeedInEnergy3 |
| 4163H | 2 | Year_FeedInEnergy3| UInt32     | -2 | kWh | R | Year_FeedInEnergy3 |
| 4165H | 2 | Total_FeedInEnergy3| UInt32    | -2 | kWh | R | Total_FeedInEnergy3 |

---

### 4.4 Peripheral Device Data Register Definition
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| A000H | 1 | BatNum | UInt16 | 0 | | R | BatNum |
| A001H | 1 | BatCapcity | UInt16 | 0 | AH | R | BatCapcity |
| A002H | 1 | Bat1FaultMSG | UInt16 | 0 | | R | Bat1FaultMSG |
| A003H | 1 | Bat1WarnMSG | UInt16 | 0 | | R | Bat1WarnMSG |
| A004H | 1 | Bat2FaultMSG | UInt16 | 0 | | R | Bat2FaultMSG |
| A005H | 1 | Bat2WarnMSG | UInt16 | 0 | | R | Bat2WarnMSG |
| A006H | 1 | Bat3FaultMSG | UInt16 | 0 | | R | Bat3FaultMSG |
| A007H | 1 | Bat3WarnMSG | UInt16 | 0 | | R | Bat3WarnMSG |
| A008H | 1 | Bat4FaultMSG | UInt16 | 0 | | R | Bat4FaultMSG |
| A009H | 1 | Bat4WarnMSG | UInt16 | 0 | | R | Bat4WarnMSG |
| A00AH | 2 | Reserve | UInt16 | 0 | | R | Reserve |
| A00CH | 1 | Bat1SOC | UInt16 | -2 | % | R | Bat1SOC |
| A00DH | 1 | Bat1SOH | UInt16 | -2 | % | R | Bat1SOH |
| A00EH | 1 | Bat1Voltage | UInt16 | -1 | V | R | Bat1Voltage |
| A00FH | 1 | Bat1Current | Int16 | -2 | A | R | Bat1Current |
| A010H | 1 | Bat1Temperature| Int16 | -1 | ℃ | R | Bat1Temperature |
| A011H | 1 | Bat1CycleNum | UInt16 | 0 | | R | Bat1CycleNum |
| A012H | 1 | Bat2SOC | UInt16 | -2 | % | R | Bat2SOC |
| A013H | 1 | Bat2SOH | UInt16 | -2 | % | R | Bat2SOH |
| A014H | 1 | Bat2Voltage | UInt16 | -1 | V | R | Bat2Voltage |
| A015H | 1 | Bat2Current | Int16 | -2 | A | R | Bat2Current |
| A016H | 1 | Bat2Temperature| Int16 | -1 | ℃ | R | Bat2Temperature |
| A017H | 1 | Bat2CycleNum | UInt16 | 0 | | R | Bat2CycleNum |
| A018H | 1 | Bat3SOC | UInt16 | -2 | % | R | Bat3SOC |
| A019H | 1 | Bat3SOH | UInt16 | -2 | % | R | Bat3SOH |
| A01AH | 1 | Bat3Voltage | UInt16 | -1 | V | R | Bat3Voltage |
| A01BH | 1 | Bat3Current | Int16 | -2 | A | R | Bat3Current |
| A01CH | 1 | Bat3Temperature| Int16 | -1 | ℃ | R | Bat3Temperature |
| A01DH | 1 | Bat3CycleNum | UInt16 | 0 | | R | Bat3CycleNum |
| A01EH | 1 | Bat4SOC | UInt16 | -2 | % | R | Bat4SOC |
| A01FH | 1 | Bat4SOH | UInt16 | -2 | % | R | Bat4SOH |
| A020H | 1 | Bat4Voltage | UInt16 | -1 | V | R | Bat4Voltage |
| A021H | 1 | Bat4Current | Int16 | -2 | A | R | Bat4Current |
| A022H | 1 | Bat4Temperature| Int16 | -1 | ℃ | R | Bat4Temperature |
| A023H | 1 | Bat4CycleNum | UInt16 | 0 | | R | Bat4CycleNum |
| A024H | 20 | Reserve | UInt16 | 0 | | R | Reserve |
| A038H | 2 | Meter_A_ImpEp | UInt32 | -2 | kWh | R | Meter_A_ImpEp |
| A03AH | 2 | Meter_A_ExpEp | UInt32 | -2 | kWh | R | Meter_A_ExpEp |
| A03CH | 1 | Meter_A_Status | UInt16 | 0 | | R | Meter_A_Status |
| A03DH | 1 | Meter_A_Volt1 | UInt16 | -1 | V | R | Meter_A_Volt1 |
| A03EH | 1 | Meter_A_Curr1 | Int16 | -2 | A | R | Meter_A_Curr1 |
| A03FH | 1 | Meter_A_PowerWatt1| Int16| 0 | W | R | Meter_A_PowerWatt1 |
| A040H | 1 | Meter_A_PowerVA1| UInt16 | 0 | VA | R | Meter_A_PowerVA1 |
| A041H | 1 | Meter_A_PowerFactor1| Int16| -3| | R | Meter_A_PowerFactor1 |
| A042H | 1 | Meter_A_Freq1 | UInt16 | -2 | Hz | R | Meter_A_Freq1 |
| A043H | 1 | Meter_A_Volt2 | UInt16 | -1 | V | R | Meter_A_Volt2 |
| A044H | 1 | Meter_A_Curr2 | Int16 | -2 | A | R | Meter_A_Curr2 |
| A045H | 1 | Meter_A_PowerWatt2| Int16| 0 | W | R | Meter_A_PowerWatt2 |
| A046H | 1 | Meter_A_PowerVA2| UInt16 | 0 | VA | R | Meter_A_PowerVA2 |
| A047H | 1 | Meter_A_PowerFactor2| Int16| -3| | R | Meter_A_PowerFactor2 |
| A048H | 1 | Meter_A_Freq2 | UInt16 | -2 | Hz | R | Meter_A_Freq2 |
| A049H | 1 | Meter_A_Volt3 | UInt16 | -1 | V | R | Meter_A_Volt3 |
| A04AH | 1 | Meter_A_Curr3 | Int16 | -2 | A | R | Meter_A_Curr3 |
| A04BH | 1 | Meter_A_PowerWatt3| Int16| 0 | W | R | Meter_A_PowerWatt3 |
| A04CH | 1 | Meter_A_PowerVA3| UInt16 | 0 | VA | R | Meter_A_PowerVA3 |
| A04DH | 1 | Meter_A_PowerFactor3| Int16| -3| | R | Meter_A_PowerFactor3 |
| A04EH | 1 | Meter_A_Freq3 | UInt16 | -2 | Hz | R | Meter_A_Freq3 |
| A04FH | 2 | Meter_B_ImpEp | UInt32 | -2 | kWh | R | Meter_B_ImpEp |
| A051H | 2 | Meter_B_ExpEp | UInt32 | -2 | kWh | R | Meter_B_ExpEp |
| A053H | 1 | Meter_B_Status | UInt16 | 0 | | R | Meter_B_Status |
| A054H | 1 | Meter_B_Volt1 | UInt16 | -1 | V | R | Meter_B_Volt1 |
| A055H | 1 | Meter_B_Curr1 | Int16 | -2 | A | R | Meter_B_Curr1 |
| A056H | 1 | Meter_B_PowerWatt1| Int16| 0 | W | R | Meter_B_PowerWatt1 |
| A057H | 1 | Meter_B_PowerVA1| UInt16 | 0 | VA | R | Meter_B_PowerVA1 |
| A058H | 1 | Meter_B_PowerFactor1| Int16| -3| | R | Meter_B_PowerFactor1 |
| A059H | 1 | Meter_B_Freq1 | UInt16 | -2 | Hz | R | Meter_B_Freq1 |
| A05AH | 1 | Meter_B_Volt2 | UInt16 | -1 | V | R | Meter_B_Volt2 |
| A05BH | 1 | Meter_B_Curr2 | Int16 | -2 | A | R | Meter_B_Curr2 |
| A05CH | 1 | Meter_B_PowerWatt2| Int16| 0 | W | R | Meter_B_PowerWatt2 |
| A05DH | 1 | Meter_B_PowerVA2| UInt16 | 0 | VA | R | Meter_B_PowerVA2 |
| A05EH | 1 | Meter_B_PowerFactor2| Int16| -3| | R | Meter_B_PowerFactor2 |
| A05FH | 1 | Meter_B_Freq2 | UInt16 | -2 | Hz | R | Meter_B_Freq2 |
| A060H | 1 | Meter_B_Volt3 | UInt16 | -1 | V | R | Meter_B_Volt3 |
| A061H | 1 | Meter_B_Curr3 | Int16 | -2 | A | R | Meter_B_Curr3 |
| A062H | 1 | Meter_B_PowerWatt3| Int16| 0 | W | R | Meter_B_PowerWatt3 |
| A063H | 1 | Meter_B_PowerVA3| UInt16 | 0 | VA | R | Meter_B_PowerVA3 |
| A064H | 1 | Meter_B_PowerFactor3| Int16| -3| | R | Meter_B_PowerFactor3 |
| A065H | 1 | Meter_B_Freq3 | UInt16 | -2 | Hz | R | Meter_B_Freq3 |

---

### 4.5 Setting Data Register Definition
| Address | SIZE (Word) | Register Name | Data Type | Magnification | Unit | Attributes | Register Description / Remark |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| 3303H | 1 | EEVersion | UInt16 | | | R | EEVersion |
| 3304H | 1 | CtrlHWVersion | UInt16 | | | R/W | CtrlHWVersion |
| 3305H | 1 | PowerHWVersion | UInt16 | | | R/W | PowerHWVersion |
| 3306H | 1 | MachType | UInt16 | | | R/W | MachType |
| 3307H | 1 | MachPower | UInt16 | | | R/W | MachPower |
| 3308H | 1 | SafetyType | UInt16 | | | R/W | SafetyType |
| 3309H | 1 | FunMask | UInt16 | | | R/W | FunMask (See section 4.8 for mapping) |
| 330DH | 1 | BusVoltHigh | UInt16 | -1 | V | R/W | BusVoltHigh |
| 3311H | 1 | DCIMax | UInt16 | 0 | mA | R/W | DCIMax |
| 3313H | 1 | GVConsisMax | UInt16 | -1 | V | R/W | GVConsisMax |
| 3314H | 1 | GFConsisMax | UInt16 | -1 | V | R/W | GFConsisMax |
| 3319H | 1 | ISOLimit | UInt16 | 0 | kΩ | R/W | ISOLimit |
| 331AH | 1 | ReConnTime | UInt16 | 0 | S | R/W | ReConnTime |
| 331BH | 1 | ErrClrTime | UInt16 | 0 | S | R/W | ErrClrTime |
| 331CH | 1 | PowerLimited | UInt16 | -1 | kW | R/W | PowerLimited.<br>0: No limit, allow to run at the maximum common rate |
| 331DH | 1 | ReactiveMode | UInt16 | | | R/W | ReactiveMode.<br>0: capacitive adjustment (kW)<br>1: inductive adjustment (kW)<br>2: capacitive power factor adjustment<br>3: inductive power factor adjustment<br>4: curve mode |
| 331EH | 1 | ReactiveValue | UInt16 | -3 | | R/W | ReactiveValue. Unit: kW or % |
| 3324H | 1 | GridVolt10mHigh| UInt16 | -1 | V | R/W | GridVolt10mHigh |
| 3325H | 1 | GridVoltHigh | UInt16 | -1 | V | R/W | GridVoltHigh |
| 3326H | 1 | GridVoltLow | UInt16 | -1 | V | R/W | GridVoltLow |
| 3327H | 1 | GridFreqHigh | UInt16 | -2 | Hz | R/W | GridFreqHigh |
| 3328H | 1 | GridFreqLow | UInt16 | -2 | Hz | R/W | GridFreqLow |
| 3329H | 1 | GridVoltHigh2 | UInt16 | -1 | V | R/W | GridVoltHigh2 |
| 332AH | 1 | GridVoltLow2 | UInt16 | -1 | V | R/W | GridVoltLow2 |
| 332BH | 1 | GridFreqHigh2 | UInt16 | -2 | Hz | R/W | GridFreqHigh2 |
| 332CH | 1 | GridFreqLow2 | UInt16 | -2 | Hz | R/W | GridFreqLow2 |
| 332DH | 1 | GridVoltHighTripTime | UInt16 | 0 | 20ms | R/W | GridVoltHighTripTime. Unit 20ms. For example: A value of 50 corresponds to 1000ms. |
| 332EH | 1 | GridVoltLowTripTime | UInt16 | 0 | 20ms | R/W | GridVoltLowTripTime |
| 332FH | 1 | GridVoltHighTripTime2 | UInt16 | 0 | 20ms | R/W | GridVoltHighTripTime2 |
| 3330H | 1 | GridVoltLowTripTime2 | UInt16 | 0 | 20ms | R/W | GridVoltLowTripTime2 |
| 3331H | 1 | GridFreqHighTripTime | UInt16 | 0 | 20ms | R/W | GridFreqHighTripTime |
| 3332H | 1 | GridFreqLowTripTime | UInt16 | 0 | 20ms | R/W | GridFreqLowTripTime |
| 3333H | 1 | GridFreqHighTripTime2| UInt16 | 0 | 20ms | R/W | GridFreqHighTripTime2 |
| 3334H | 1 | GridFreqLowTripTime2 | UInt16 | 0 | 20ms | R/W | GridFreqLowTripTime2 |
| 3335H | 1 | PowerAdjCoff1 | UInt16 | 0 | | R/W | PowerAdjCoff1 |
| 3336H | 1 | PowerAdjCoff2 | UInt16 | 0 | | R/W | PowerAdjCoff2 |
| 3337H | 1 | InverterStop | UInt16 | 0 | | R/W | InverterStop |
| 3338H | 1 | FunMaskEx | UInt16 | 0 | | R/W | FunMaskEx |
| 3348H | 1 | GridChargPowerLimit | UInt16 | 0 | W | R/W | GridChargPowerLimit. Default 2500W |
| 3349H | 1 | GridFeedPowerLimit | UInt16 | 0 | W | R/W | GridFeedPowerLimit. Default 2500W |
| 334AH | 1 | BatType | UInt16 | 0 | | R/W | BatType. Default 0. 0=lead-acid battery, 1=lithium battery |
| 334BH | 1 | BatCapcity | UInt16 | 0 | AH | R/W | BatCapcity. Default 100AH |
| 334CH | 1 | BatProtHigh | UInt16 | -1 | V | R/W | BatProtHigh. Default 60V (Range: 50~60V) |
| 334DH | 1 | BatProtLow | UInt16 | -1 | V | R/W | BatProtLow. Default 46V (Range: 40~52V) |
| 334EH | 1 | BatOpenVolt | UInt16 | -1 | V | R/W | BatOpenVolt. Default 38V (Range: 12~42V) |
| 334FH | 1 | BatLowVolt | UInt16 | -1 | V | R/W | BatLowVolt. Default 42V (Range: 40~48V) |
| 3350H | 1 | BatDisDepth | UInt16 | 0 | % | R/W | BatDisDepth. Default 80% (Range: 20~95%). Valid in off-grid mode. |
| 3351H | 1 | BatFloatVolt | UInt16 | -1 | V | R/W | BatFloatVolt. Default 54V (Range: 48~58V) |
| 3352H | 1 | BatFloatTime | UInt16 | 0 | min | R/W | BatFloatTime. Default 120 (Range: 0~65535) |
| 3353H | 1 | BatChgCurrLimit| UInt16 | -1 | A | R/W | BatChgCurrLimit. Default 50A (Range: 5~50A) |
| 3354H | 1 | BatDisCurrLimit| UInt16 | -1 | A | R/W | BatDisCurrLimit. Default 100A (Range: 5~120A) |
| 3355H | 1 | BatAutoWakeEn | UInt16 | 0 | | R/W | BatAutoWakeEn. The default is 0. 0=disable, 1=enable (only allowed when battery type is lithium) |
| 3371H | 1 | ACC_UserMode | UInt16 | 0 | | R/W | ACC_UserMode.<br>1: Automatic scheduling mode<br>2: Time-of-use electricity pricing model<br>3: Backup mode<br>4: Manual maintenance mode |
| 3372H | 1 | ACC_EPSEn | UInt16 | 0 | | R/W | ACC_EPSEn. 0: Disable; 1: Enable |
| 3373H | 1 | ACC_BatSetSOC_H| UInt16 | 0 | % | R/W | ACC_BatSetSOC_H. The default value is 80, valid in grid-connected mode. |
| 3374H | 1 | ACC_BatSetSOC_L| UInt16 | 0 | % | R/W | ACC_BatSetSOC_L. The default value is 40, valid in grid-connected mode. |
| 3375H | 1 | CommProtocolType| UInt16| 0 | | R/W | CommProtocolType. 1: SAJ, 2: Alpha.ESS |
| 3376H | 1 | SafetyModeCtrl | UInt16 | 0 | | R/W | SafetyModeCtrl. Bit 10 (DRM enable bit): 0: Off, 1: On |
| 3377H | 1 | BackModSOCRetain| UInt16| 0 | % | R/W | BackModSOCRetain. Default 80 |
| 3378H | 1 | DRMCertification| UInt16| 0 | | R/W | DRMCertification. 0: AS4777.2, 1: AS4755.3 |
| 3600H | 1 | GridchargeEnable| UInt16 | 0 | | R | Timed grid charging enable. 1: Enable, 0: Prohibit |
| 3601H | 1 | DischargeEnable | UInt16 | 0 | | R | Timed grid-connected battery discharge enable. 1: Enable, 0: Prohibit |
| 3602H | 1 | Loader_Control | UInt16 | 0 | | R | (PutOn/CutOff)Loader drop/cut. 1: Drop load, 0: Cut load |
| 3603H | 1 | Exc_Sell_Energy | UInt16 | 0 | | R | Selling surplus electricity. 1: Enable, 0: Prohibit |
| 3604H | 1 | Charge_time_enable_control | UInt16 | 0 | | R/W | Charge time setting enable bit. Each bit represents an enabled profile (Bit 0 = 1st, Bit 1 = 2nd...) |
| 3605H | 1 | Discharge_time_enable_control | UInt16 | 0 | | R/W | Discharge time setting enable bit. Each bit represents an enabled profile (Bit 0 = 1st, Bit 1 = 2nd...) |
| 3606H | 1 | First_charge_start_time | HEX | 0 | | R/W | The first charging start time. High byte is hour, low byte is minute; hh:mm |
| 3607H | 1 | First_charge_end_time | HEX | 0 | | R/W | The first charging end time. High byte is hour, low byte is minute; hh:mm |
| 3608H | 1 | First_charge_power_time | HEX | 0 | | R/W | The first charging date and power. High byte indicates the day of the week via bitmask (e.g., 0b0100 is Wednesday); low byte indicates power (e.g., 1 is 1% of standard power). |
| 3609H | 1 | Second_charge_start_time | HEX | 0 | | R/W | The second charging start time. High byte is hour, low byte is minute; hh:mm |
| 360AH | 1 | Second_charge_end_time | HEX | 0 | | R/W | The second charging end time. High byte is hour, low byte is minute; hh:mm |
| 360BH | 1 | Second_charge_power_time | HEX | 0 | | R/W | The second charging date and power. High byte = day mask, low byte = power %. |
| 360CH | 1 | Third_charge_start_time | HEX | 0 | | R/W | The third charging start time. 高字节为小时，低字节为分钟；hh:mm |
| 360DH | 1 | Third_charge_end_time | HEX | 0 | | R/W | The third charging end time. 高字节为小时，低字节为分钟；hh:mm |
| 360EH | 1 | Third_charge_power_time | HEX | 0 | | R/W | Article 3 Charging date and power. High byte = day mask, low byte = power %. |
| 360FH | 1 | Fourth_charge_start_time | HEX | 0 | | R/W | Article 4 Charging start time. High byte is hour, low byte is minute; hh:mm |
| 3610H | 1 | Fourth_charge_end_time | HEX | 0 | | R/W | Article 4 Charging end time. High byte is hour, low byte is minute; hh:mm |
| 3611H | 1 | Fourth_charge_power_time | HEX | 0 | | R/W | Article 4 Charging date and power. High byte = day mask, low byte = power %. |
| 3612H | 1 | Fifth_charge_start_time | HEX | 0 | | R/W | Article 5 Charging start time. High byte is hour, low byte is minute; hh:mm |
| 3613H | 1 | Fifth_charge_end_time | HEX | 0 | | R/W | Article 5 Charging end time. High byte is hour, low byte is minute; hh:mm |
| 3614H | 1 | Fifth_charge_power_time | HEX | 0 | | R/W | Article 5 Charging date and power. High byte = day mask, low byte = power %. |
| 3615H | 1 | Sixth_charge_start_time | HEX | 0 | | R/W | Article 6 Charging start time. High byte is hour, low byte is minute; hh:mm |
| 3616H | 1 | Sixth_charge_end_time | HEX | 0 | | R/W | Article 6 Charging end time. High byte is hour, low byte is minute; hh:mm |
| 3617H | 1 | Sixth_charge_power_time | HEX | 0 | | R/W | Article 6 Charging date and power. High byte = day mask, low byte = power %. |
| 3618H | 1 | Seventh_charge_start_time| HEX | 0 | | R/W | Article 7 Charging start time. High byte is hour, low byte is minute; hh:mm |
| 3619H | 1 | Seventh_charge_end_time | HEX | 0 | | R/W | Article 7 Charging end time. High byte is hour, low byte is minute; hh:mm |
| 361AH | 1 | Seventh_charge_power_time| HEX | 0 | | R/W | Article 7 Charging date and power. High byte = day mask, low byte = power %. |
| 361BH | 1 | First_discharge_start_time| HEX | 0 | | R/W | The first discharge start time. High byte is hour, low byte is minute; hh:mm |
| 361CH | 1 | First_discharge_end_time | HEX | 0 | | R/W | The first discharge end time. High byte is hour, low byte is minute; hh:mm |
| 361DH | 1 | First_discharge_power_time| HEX | 0 | | R/W | The first discharge date and power. High byte = day mask, low byte = power %. |
| 361EH | 1 | Second_discharge_start_time| HEX| 0 | | R/W | The second discharge start time. High byte is hour, low byte is minute; hh:mm |
| 361FH | 1 | Second_discharge_end_time| HEX | 0 | | R/W | The second discharge end time. High byte is hour, low byte is minute; hh:mm |
| 3620H | 1 | Second_discharge_power_time| HEX| 0 | | R/W | The second discharge date and power. High byte = day mask, low byte = power %. |
| 3621H | 1 | Third_discharge_start_time| HEX | 0 | | R/W | The third discharge start time. High byte is hour, low byte is minute; hh:mm |
| 3622H | 1 | Third_discharge_end_time | HEX | 0 | | R/W | The third discharge end time. High byte is hour, low byte is minute; hh:mm |
| 3623H | 1 | Third_discharge_power_time| HEX | 0 | | R/W | Article 3 Discharge date and power. High byte = day mask, low byte = power %. |
| 3624H | 1 | Fourth_discharge_start_time| HEX| 0 | | R/W | The fourth discharge start time. High byte is hour, low byte is minute; hh:mm |
| 3625H | 1 | Fourth_discharge_end_time| HEX  | 0 | | R/W | Article 4 Discharge end time. High byte is hour, low byte is minute; hh:mm |
| 3626H | 1 | Fourth_discharge_power_time| HEX| 0 | | R/W | Article 4 Discharge date and power. High byte = day mask, low byte = power %. |
| 3627H | 1 | Fifth_discharge_start_time| HEX | 0 | | R/W | Article 5 Discharge start time. High byte is hour, low byte is minute; hh:mm |
| 3628H | 1 | Fifth_discharge_end_time | HEX  | 0 | | R/W | Article 5 Discharge end time. High byte is hour, low byte is minute; hh:mm |
| 3629H | 1 | Fifth_discharge_power_time| HEX | 0 | | R/W | Article 5 Discharge date and power. High byte = day mask, low byte = power %. |
| 362AH | 1 | Sixth_discharge_start_time| HEX | 0 | | R/W | Article 6 Discharge start time. High byte is hour, low byte is minute; hh:mm |
| 362BH | 1 | Sixth_discharge_end_time | HEX  | 0 | | R/W | Article 6 Discharge end time. High byte is hour, low byte is minute; hh:mm |
| 362CH | 1 | Sixth_discharge_power_time| HEX | 0 | | R/W | Article 6 Discharge start time. High byte = day mask, low byte = power %. |
| 362DH | 1 | Seventh_discharge_start_time| HEX| 0 | | R/W | Article 7 Discharge start time. High byte is hour, low byte is minute; hh:mm |
| 362EH | 1 | Seventh_discharge_end_time| HEX  | 0 | | R/W | Article 7 Discharge end time. High byte is hour, low byte is minute; hh:mm |
| 362FH | 1 | Seventh_discharge_power_time| HEX| 0 | | R/W | Article 7 Discharge date and power. High byte = day mask, low byte = power %. |
| 3630H | 1 | Meter_enable | UInt16 | 0 | | R/W | Meter enable. 0: disable, 1: 1 meter, 2: 2 meters |
| 3631H | 1 | Meter_addr | UInt16 | 0 | | R/W | The communication address of the meter. Range: 1 - 255 |
| 3632H | 1 | Buzzer_on-off | UInt16 | 0 | | R/W | Buzzer switch enable. 0: enable, 1: disable |
| 3633H | 1 | RS485_Addr | UInt16 | | | R/W | RS485 communication address. Range: 1 ~ 127 |
| 3634H | 1 | RS485_BaudRate | UInt16 | | | R/W | RS485 Communication baud rate.<br>0: 9600, 1: 4800, 2: 2400, 3: 1200 |

---

### 4.6 Error Code Definition

#### Host Fault Code Definition (Master Controller)
| Code / Bit | Fault Definition (EN) | Fault Definition (Alternative/Duplicate) |
| :---: | :--- | :--- |
| **1** | Lost Com.M<->S Err | Lost Com.M<->S Err |
| **2** | Temp.High Err | Temp.High Err |
| **3** | Temp.Low Err | Temp.Low Err |
| **4** | DCI Err | DCI Err |
| **5** | SynPulse Err | SynPulse Err |
| **6** | Relay Err | Relay Err |
| **7** | Eeprom Err | Eeprom Err |
| **8** | Bat Input Short Err | Bat Input Short Err |
| **9** | Bat Volt.High Err | Bat Volt.High Err |
| **10** | Bat Open Err | Bat Open Err |
| **11** | HWDc Curr.High Err | HWDc Curr.High Err |
| **12** | Bat Discharge Err | Bat Discharge Err |
| **13** | BatCtrl Curr.High Err | BatCtrl Curr.High Err |
| **14** | BusSoftTimeOut Err | BusSoftTimeOut Err |
| **15** | Bus Volt.High Err | Bus Volt.High Err |
| **16** | Bus Volt.Low Err | Bus Volt.Low Err |
| **17** | HWBus Volt.High Err | HWBus Volt.High Err |
| **18** | Inv Curr.High Err | Inv Curr.High Err |
| **19** | HWInv Curr.High Err | HWInv Curr.High Err |
| **20** | Inv Short Err | Inv Short Err |
| **21** | Over Load Err | Over Load Err |
| **22** | Reserved (bit 22) | Reserved (bit 22) |
| **23** | Reserved (bit 23) | Reserved (bit 23) |
| **24** | Reserved (bit 24) | Reserved (bit 24) |
| **25** | Grid Volt.High Warn | Grid Volt.High Warn |
| **26** | Grid Volt.Low Warn | Grid Volt.Low Warn |
| **27** | Grid Freq.High Warn | Grid Freq.High Warn |
| **28** | Grid Freq.Low Warn | Grid Freq.Low Warn |
| **29** | Grid Loss Warn | Grid Loss Warn |
| **30** | Grid Volt.10min Warn | Grid Volt.10min Warn |
| **31** | Over Load Warn | Over Load Warn |
| **32** | Reserved (bit 32) | Reserved (bit 32) |

#### Slave Fault Code Definition (Slave Controller)
| Code / Bit | Fault Definition (EN) | Fault Definition (Alternative/Duplicate) |
| :---: | :--- | :--- |
| **33** | Fan Err | Fan Err |
| **34** | Out Insert Err | Out Insert Err |
| **35** | Inv Wave Err | Inv Wave Err |
| **36** | BMS Lost.Conn Err | BMS Lost.Conn Err |
| **37** | Reserved (bit 37) | Reserved (bit 37) |
| **38** | Reserved (bit 38) | Reserved (bit 38) |
| **39** | Reserved (bit 39) | Reserved (bit 39) |
| **40** | Reserved (bit 40) | Reserved (bit 40) |
| **41** | Reserved (bit 41) | Reserved (bit 41) |
| **42** | Reserved (bit 42) | Reserved (bit 42) |
| **43** | Reserved (bit 43) | Reserved (bit 43) |
| **44** | Reserved (bit 44) | Reserved (bit 44) |
| **45** | Reserved (bit 45) | Reserved (bit 45) |
| **46** | Reserved (bit 46) | Reserved (bit 46) |
| **47** | Reserved (bit 47) | Reserved (bit 47) |
| **48** | Reserved (bit 48) | Reserved (bit 48) |
| **49** | Grid Volt.Consis Warn | Grid Volt.Consis Warn |
| **50** | Grid Freq.Consis Warn | Grid Freq.Consis Warn |
| **51** | GND Loss Warn | GND Loss Warn |
| **52** | LN Wrong Warn | LN Wrong Warn |
| **53** | Can Com Lost | Can Com Lost |
| **54** | Bat Soc Low Warn | Bat Soc Low Warn |
| **55** | Bat Volt High Warn | Bat Volt High Warn |
| **56** | Bat Volt Low Warn | Bat Volt Low Warn |
| **57** | Grid Volt.High Warn | Grid Volt.High Warn |
| **58** | Grid Volt.Low Warn | Grid Volt.Low Warn |
| **59** | Grid Freq.High Warn | Grid Freq.High Warn |
| **60** | Grid Freq.Low Warn | Grid Freq.Low Warn |
| **61** | Grid Loss Warn | Grid Loss Warn |
| **62** | Reserved (bit 62) | Reserved (bit 62) |
| **63** | Reserved (bit 63) | Reserved (bit 63) |
| **64** | Reserved (bit 64) | Reserved (bit 64) |

#### Display Board Fault Code Definition
| Code / Bit | Fault Definition (EN) | Fault Definition (CN) |
| :---: | :--- | :--- |
| **65** | Lost Com.H<->M Err | Displayboard communication lost |
| **66** | HMI Eeprom Err | memory failure |
| **67** | HMI RTC Err | RTC error |
| **68** | BMS Device Err | BMS device error |
| **69** | Reserved (bit 69) | Reserved (bit 69) |
| **70** | Reserved (bit 70) | Reserved (bit 70) |
| **71** | Reserved (bit 71) | Reserved (bit 71) |
| **72** | Reserved (bit 72) | Reserved (bit 72) |
| **73** | Reserved (bit 73) | Reserved (bit 73) |
| **74** | Reserved (bit 74) | Reserved (bit 74) |
| **75** | Reserved (bit 75) | Reserved (bit 75) |
| **76** | Reserved (bit 76) | Reserved (bit 76) |
| **77** | Reserved (bit 77) | Reserved (bit 77) |
| **78** | Reserved (bit 78) | Reserved (bit 78) |
| **79** | Reserved (bit 79) | Reserved (bit 79) |
| **80** | Reserved (bit 80) | Reserved (bit 80) |
| **81** | BMS Cell Volt.H Warn | Battery cell overvoltage warning |
| **82** | BMS Cell Volt.L Warn | Battery cell undervoltage warning |
| **83** | BMS CHG Curr.H Warn | Overcharge current warning |
| **84** | Reserved (bit 84) | Reserved (bit 84) |
| **85** | BMS DCHG Curr.H Warn | Excessive discharge current warning |
| **86** | BMS DCHG Temp Warn | Discharge temperature high warn |
| **87** | BMS CHG Temp Warn | Charge temperature high warn |
| **88** | BMS Voltage Low Warn | BMS Voltage Low Warn |
| **89** | BMS Lost.Conn Warn | BMS lost communication warn |
| **90** | Reserved (bit 90) | Reserved (bit 90) |
| **91** | Meter Lost Com Warn | Meter Lost Com Warn |
| **92** | DRM0 Warn | DRM0 Warn |
| **93** | Reserved (bit 93) | Reserved (bit 93) |
| **94** | Reserved (bit 94) | Reserved (bit 94) |
| **95** | Reserved (bit 95) | Reserved (bit 95) |
| **96** | Reserved (bit 96) | Reserved (bit 96) |

---

### 4.7 BMS Error Code Definition
| Bit Configuration | Fault MSG | Warn MSG |
| :---: | :--- | :--- |
| **Bit 0** | Reserved | Reserved |
| **Bit 1** | Over voltage | High voltage |
| **Bit 2** | Under voltage | Low voltage |
| **Bit 3** | Over temp. | High temp. |
| **Bit 4** | Under temp. | Low temp. |
| **Bit 5** | Over MOSFET temp. | Over MOSFET temp. |
| **Bit 6** | Over environment temp. | Over environment temp. |
| **Bit 7** | Over current discharge | High current discharge |
| **Bit 8** | Over current charge | High current charge |
| **Bit 9** | Short circuit | Short circuit |
| **Bit 10** | Reserved | Reserved |
| **Bit 11** | BMS internal | BMS internal |
| **Bit 12** | Voltage detection failure | Reserved |
| **Bit 13** | Current detection failure | Reserved |
| **Bit 14** | Temp. detection failure | Reserved |
| **Bit 15** | MOSFET detection failure | Reserved |

---

### 4.8 0x3309 Register Definition
| Address | Bit | Register Name | Data Type | Magnification | Unit | Attributes | Register Description | Remark |
| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **0x3309** | bit0 | RelayCheck | | 0 | | | Relay detection enable bit | 0=disable, 1=enable |
| | bit1 | ISOCheck | | 0 | | | ISO detection enable bit | 0=disable, 1=enable |
| | bit2 | GFCIDevCheck | | 0 | | | Earth leakage current device self-check enable bit | 0=disable, 1=enable |
| | bit3 | GFCICheck | | 0 | | | Earth leakage current detection enable bit | 0=disable, 1=enable |
| | bit4 | DciCheck | | 0 | | | Grid current DC component detection enable bit | 0=disable, 1=enable |
| | bit5 | DciAdjust | | 0 | | | Grid current DC component control enable bit | 0=disable, 1=enable |
| | bit6 | AntiIsland | | 0 | | | Active Islanding Detection Enable Bit | 0=disable, 1=enable |
| | bit7 | FANCheck | | 0 | | | Fan Detection Enable Bit | 0=disable, 1=enable |
| | bit8 | Rsvd8 | | 0 | | | Reserved8 | 0=disable, 1=enable |
| | bit9 | Rsvd9 | | 0 | | | Reserved9 | 0=disable, 1=enable |
| | bit10 | Rsvd10 | | 0 | | | Reserved10 | 0=disable, 1=enable |
| | bit11 | LNPECheck | | 0 | | | Grid connection detection enable bit | 0=disable, 1=enable |
| | bit12 | DviAdjust | | 0 | | | Output voltage DC component control enable bit | 0=disable, 1=enable |
| | bit13 | OutInsertCheck | | 0 | | | Output abnormal access detection enable bit | 0=disable, 1=enable |
| | bit14 | InvWaveCheck | | 0 | | | Inverter wave detection enable bit | 0=disable, 1=enable |
| | bit15 | PvLoadFuncEn | | 0 | | | PV Independent Load Enable Bit | 0=disable, 1=enable |