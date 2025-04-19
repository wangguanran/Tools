import re
from datetime import datetime
import os

# 在文件开头添加颜色代码定义
class Colors:
    """ANSI颜色代码"""
    HEADER = '\033[95m'    # 紫色
    BLUE = '\033[94m'      # 蓝色
    CYAN = '\033[96m'      # 青色
    GREEN = '\033[92m'     # 绿色
    YELLOW = '\033[93m'    # 黄色
    RED = '\033[91m'       # 红色
    BOLD = '\033[1m'       # 粗体
    UNDERLINE = '\033[4m'  # 下划线
    END = '\033[0m'        # 结束颜色

def parse_reg00(value):
    """解析cx2560x的00寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        en_hiz = (value >> 7) & 0x1        # bit 7
        dpdm_dis = (value >> 6) & 0x1      # bit 6
        stat_dis = (value >> 5) & 0x1      # bit 5
        iindpm = value & 0x1F              # bits [4:0]
        
        # 计算输入电流限制值
        input_current = 100 + (iindpm * 100)  # 根据位值计算实际电流值，单位mA
        
        result = {
            'EN_HIZ': {
                'value': en_hiz,
                'description': 'Enable' if en_hiz == 1 else 'Disable (default)'
            },
            'DPDM_DIS': {
                'value': dpdm_dis,
                'description': 'Disable' if dpdm_dis == 1 else 'Enable (default)'
            },
            'STAT_DIS': {
                'value': stat_dis,
                'description': 'Disable' if stat_dis == 1 else 'Enable (default)'
            },
            'IINDPM': {
                'value': iindpm,
                'current': f"{input_current}mA",
                'description': f"Input Current Limit: {input_current}mA"
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器00值时出错: {e}")
        return None

def parse_reg01(value):
    """解析cx2560x的01寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        reserved = (value >> 7) & 0x1      # bit 7: Reserved
        wd_rst = (value >> 6) & 0x1        # bit 6: WD_RST
        otg_config = (value >> 5) & 0x1    # bit 5: OTG_CONFIG
        chg_config = (value >> 4) & 0x1    # bit 4: CHG_CONFIG
        sys_min = value & 0x0F             # bits [3:0]: SYS_MIN[2:0]
        
        # 解析系统最小电压
        sys_min_voltage = {
            0: "2.6V",
            1: "2.8V",
            2: "3.0V",
            3: "3.2V",
            4: "3.4V",
            5: "3.5V",
            6: "3.6V",
            7: "3.7V"
        }.get(sys_min, "Unknown")
        
        result = {
            'Reserved': {
                'value': reserved,
                'description': 'Reserved bit'
            },
            'WD_RST': {
                'value': wd_rst,
                'description': 'Reset (Back to 0 after timer reset)' if wd_rst == 1 else 'Normal'
            },
            'OTG_CONFIG': {
                'value': otg_config,
                'description': 'OTG Enable' if otg_config == 1 else 'OTG Disable (default)'
            },
            'CHG_CONFIG': {
                'value': chg_config,
                'description': 'Charge Enable (default)' if chg_config == 1 else 'Charge Disable'
            },
            'SYS_MIN': {
                'value': sys_min,
                'voltage': sys_min_voltage,
                'description': f"System Minimum Voltage: {sys_min_voltage}"
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器01值时出错: {e}")
        return None

def parse_reg02(value):
    """解析cx2560x的02寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        boost_lim = (value >> 7) & 0x1      # bit 7: BOOST_LIM
        q1_fullon = (value >> 6) & 0x1      # bit 6: Q1_FULLON
        ichg5 = (value >> 5) & 0x1          # bit 5: ICHG[5]
        ichg4 = (value >> 4) & 0x1          # bit 4: ICHG[4]
        ichg3 = (value >> 3) & 0x1          # bit 3: ICHG[3]
        ichg2 = (value >> 2) & 0x1          # bit 2: ICHG[2]
        ichg1 = (value >> 1) & 0x1          # bit 1: ICHG[1]
        ichg0 = value & 0x1                 # bit 0: ICHG[0]
        
        # 组合ICHG[5:0]位
        ichg = (ichg5 << 5) | (ichg4 << 4) | (ichg3 << 3) | (ichg2 << 2) | (ichg1 << 1) | ichg0
        
        # 计算快速充电电流值
        # 根据数据手册：
        # 000000~001101: 0mA~1170mA, 90mA per step
        # 001110~110101: 805mA~3047.5mA, 57.5mA per step
        if ichg <= 0b001101:  # 0-13
            charge_current = ichg * 90  # 90mA per step
        else:  # 14-53
            charge_current = 805 + ((ichg - 14) * 57.5)  # 从805mA开始，步进57.5mA
        
        result = {
            'BOOST_LIM': {
                'value': boost_lim,
                'description': '1.2A (default)' if boost_lim == 1 else '0.5A'
            },
            'Q1_FULLON': {
                'value': q1_fullon,
                'description': ('Use lower Q1 Rdson always (better efficiency)' if q1_fullon == 1 
                              else 'Use higher Q1 Rdson when IINDPM<700mA (default, better accuracy)')
            },
            'ICHG': {
                'value': ichg,
                'binary': f'{ichg:06b}',
                'current': f'{charge_current:.1f}mA',
                'description': f'Fast Charge Current: {charge_current:.1f}mA'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器02值时出错: {e}")
        return None

def parse_reg03(value):
    """解析cx2560x的03寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        iprechg3 = (value >> 7) & 0x1      # bit 7: IPRECHG[3]
        iprechg2 = (value >> 6) & 0x1      # bit 6: IPRECHG[2]
        iprechg1 = (value >> 5) & 0x1      # bit 5: IPRECHG[1]
        iprechg0 = (value >> 4) & 0x1      # bit 4: IPRECHG[0]
        iterm3 = (value >> 3) & 0x1        # bit 3: ITERM[3]
        iterm2 = (value >> 2) & 0x1        # bit 2: ITERM[2]
        iterm1 = (value >> 1) & 0x1        # bit 1: ITERM[1]
        iterm0 = value & 0x1               # bit 0: ITERM[0]
        
        # 组合IPRECHG[3:0]和ITERM[3:0]位
        iprechg = (iprechg3 << 3) | (iprechg2 << 2) | (iprechg1 << 1) | iprechg0
        iterm = (iterm3 << 3) | (iterm2 << 2) | (iterm1 << 1) | iterm0
        
        # 计算预充电电流和终止电流
        # IPRECHG: 偏移52mA，步进52mA
        iprechg_current = 52 + (iprechg * 52)  # 52mA offset, 52mA per step
        # ITERM: 偏移60mA，步进60mA
        iterm_current = 60 + (iterm * 60)      # 60mA offset, 60mA per step
        
        # 检查是否超过限制值
        if iprechg_current > 676:
            iprechg_current = 676  # IPRECHG > 676mA clamped to 676mA
        if iterm_current > 780:
            iterm_current = 780    # ITERM > 780mA clamped to 780mA
        
        result = {
            'IPRECHG': {
                'value': iprechg,
                'binary': f'{iprechg:04b}',
                'current': f'{iprechg_current}mA',
                'description': f'预充电电流: {iprechg_current}mA'
            },
            'ITERM': {
                'value': iterm,
                'binary': f'{iterm:04b}',
                'current': f'{iterm_current}mA',
                'description': f'终止电流: {iterm_current}mA'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器03值时出错: {e}")
        return None

def parse_reg04(value):
    """解析cx2560x的04寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        vreg5 = (value >> 7) & 0x1      # bit 7: VREG[5]
        vreg4 = (value >> 6) & 0x1      # bit 6: VREG[4]
        vreg3 = (value >> 5) & 0x1      # bit 5: VREG[3]
        vreg2 = (value >> 4) & 0x1      # bit 4: VREG[2]
        vreg1 = (value >> 3) & 0x1      # bit 3: VREG[1]
        reserved1 = (value >> 2) & 0x1   # bit 2: Reserved
        reserved0 = (value >> 1) & 0x1   # bit 1: Reserved
        vrechg = value & 0x1             # bit 0: VRECHG
        
        # 组合VREG[5:0]位
        vreg = (vreg5 << 4) | (vreg4 << 3) | (vreg3 << 2) | (vreg2 << 1) | vreg1
        
        # 计算充电电压值
        # 偏移值: 3.856V
        # 步进值: 32mV
        voltage = 3.856 + (vreg * 0.032)  # 3.856V + (VREG * 32mV)
        
        # 如果电压超过4.624V，限制为4.624V
        if voltage > 4.624:
            voltage = 4.624
        
        result = {
            'VREG': {
                'value': vreg,
                'binary': f'{vreg:05b}',
                'voltage': f'{voltage:.3f}V',
                'description': f'充电电压: {voltage:.3f}V'
            },
            'Reserved': {
                'value': (reserved1 << 1) | reserved0,
                'description': 'Reserved bits'
            },
            'VRECHG': {
                'value': vrechg,
                'description': '4.1V' if vrechg == 1 else '4.3V (default)'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器04值时出错: {e}")
        return None

def parse_reg05(value):
    """解析cx2560x的05寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        en_term = (value >> 7) & 0x1      # bit 7: EN_TERM
        reserved = (value >> 6) & 0x1      # bit 6: Reserved
        watchdog1 = (value >> 5) & 0x1     # bit 5: WATCHDOG[1]
        watchdog0 = (value >> 4) & 0x1     # bit 4: WATCHDOG[0]
        en_timer = (value >> 3) & 0x1      # bit 3: EN_TIMER
        chg_timer = (value >> 2) & 0x1     # bit 2: CHG_TIMER
        treg0 = (value >> 1) & 0x1         # bit 1: TREG[0]
        jeita_iset = value & 0x1           # bit 0: JEITA_ISET
        
        # 组合WATCHDOG[1:0]位
        watchdog = (watchdog1 << 1) | watchdog0
        
        # 解析看门狗定时器设置
        watchdog_time = {
            0: "Disable watchdog timer",
            1: "40s (default)",
            2: "80s",
            3: "160s"
        }.get(watchdog, "Unknown")
        
        result = {
            'EN_TERM': {
                'value': en_term,
                'description': 'Enable (default)' if en_term == 1 else 'Disable'
            },
            'Reserved': {
                'value': reserved,
                'description': 'Reserved bit'
            },
            'WATCHDOG': {
                'value': watchdog,
                'binary': f'{watchdog:02b}',
                'description': f'I2C Watchdog Timer: {watchdog_time}'
            },
            'EN_TIMER': {
                'value': en_timer,
                'description': 'Enable (default)' if en_timer == 1 else 'Disable'
            },
            'CHG_TIMER': {
                'value': chg_timer,
                'description': '10hrs (default)' if chg_timer == 1 else '5hrs'
            },
            'TREG': {
                'value': treg0,
                'description': '120°C (default)' if treg0 == 1 else '100°C'
            },
            'JEITA_ISET': {
                'value': jeita_iset,
                'description': '20% of CC (default)' if jeita_iset == 1 else '50% of CC'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器05值时出错: {e}")
        return None

def parse_reg06(value):
    """解析cx2560x的06寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        ovp1 = (value >> 7) & 0x1      # bit 7: OVP[1]
        ovp0 = (value >> 6) & 0x1      # bit 6: OVP[0]
        boostv1 = (value >> 5) & 0x1   # bit 5: BOOSTV[1]
        boostv0 = (value >> 4) & 0x1   # bit 4: BOOSTV[0]
        vindpm3 = (value >> 3) & 0x1   # bit 3: VINDPM[3]
        vindpm2 = (value >> 2) & 0x1   # bit 2: VINDPM[2]
        vindpm1 = (value >> 1) & 0x1   # bit 1: VINDPM[1]
        vindpm0 = value & 0x1          # bit 0: VINDPM[0]
        
        # 组合各个位域
        ovp = (ovp1 << 1) | ovp0
        boostv = (boostv1 << 1) | boostv0
        vindpm = (vindpm3 << 3) | (vindpm2 << 2) | (vindpm1 << 1) | vindpm0
        
        # 解析ACOV阈值
        ovp_voltage = {
            0: "5.5V",
            1: "6.5V (5V input, default)",
            2: "10.5V (9V input)",
            3: "14V (12V input)"
        }.get(ovp, "Unknown")
        
        # 解析Boost Mode电压
        boost_voltage = 4.87 + (boostv * 0.128)  # 基准电压4.87V，每步进0.128V
        if boost_voltage > 5.254:  # 限制最大电压
            boost_voltage = 5.254
            
        # 解析VINDPM阈值
        vindpm_voltage = 3.9 + (vindpm * 0.1)  # 基准电压3.9V，每步进0.1V
        if vindpm_voltage > 5.4:  # 限制最大电压
            vindpm_voltage = 5.4
        
        result = {
            'OVP': {
                'value': ovp,
                'binary': f'{ovp:02b}',
                'voltage': ovp_voltage,
                'description': f'ACOV threshold: {ovp_voltage}'
            },
            'BOOSTV': {
                'value': boostv,
                'binary': f'{boostv:02b}',
                'voltage': f'{boost_voltage:.3f}V',
                'description': f'Boost Mode Voltage: {boost_voltage:.3f}V'
            },
            'VINDPM': {
                'value': vindpm,
                'binary': f'{vindpm:04b}',
                'voltage': f'{vindpm_voltage:.1f}V',
                'description': f'Absolute VINDPM Threshold: {vindpm_voltage:.1f}V'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器06值时出错: {e}")
        return None

def parse_reg07(value):
    """解析cx2560x的07寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        iindet_en = (value >> 7) & 0x1      # bit 7: IINDET_EN
        tmr2x_en = (value >> 6) & 0x1       # bit 6: TMR2X_EN
        batfet_dis = (value >> 5) & 0x1     # bit 5: BATFET_DIS
        jeita_vset = (value >> 4) & 0x1     # bit 4: JEITA_VSET
        batfet_dly = (value >> 3) & 0x1     # bit 3: BATFET_DLY
        batfet_rst_en = (value >> 2) & 0x1  # bit 2: BATFET_RST_EN
        vdpm_track1 = (value >> 1) & 0x1    # bit 1: VDPM_TRACK[1]
        vdpm_track0 = value & 0x1           # bit 0: VDPM_TRACK[0]
        
        # 组合VDPM_TRACK[1:0]位
        vdpm_track = (vdpm_track1 << 1) | vdpm_track0
        
        # 解析VDPM跟踪设置
        vdpm_track_desc = {
            0: "Disable tracking function (VINDPM is set by register)",
            1: "VBAT + 200mV",
            2: "VBAT + 250mV",
            3: "Reserved"
        }.get(vdpm_track, "Unknown")
        
        result = {
            'IINDET_EN': {
                'value': iindet_en,
                'description': 'Force D+/D- detection' if iindet_en == 1 else 'Not in D+/D- detection (default)'
            },
            'TMR2X_EN': {
                'value': tmr2x_en,
                'description': 'Safety timer slowed by 2X during input DPM or thermal regulation' if tmr2x_en == 1 else 'Safety timer not slowed by 2X during input DPM or thermal regulation (default)'
            },
            'BATFET_DIS': {
                'value': batfet_dis,
                'description': 'Force BATFET off' if batfet_dis == 1 else 'Allow BATFET turn on (default)'
            },
            'JEITA_VSET': {
                'value': jeita_vset,
                'description': 'Set Charge Voltage to VREG during JEITA high temperature' if jeita_vset == 1 else 'Set Charge Voltage to VREG-200mV during JEITA high temperature (default)'
            },
            'BATFET_DLY': {
                'value': batfet_dly,
                'description': 'BATFET turn off delay by tDLY_OFF (typ. 10s) when BATFET_DIS bit is set' if batfet_dly == 1 else 'BATFET turn off immediately when BATFET_DIS bit is set (default)'
            },
            'BATFET_RST_EN': {
                'value': batfet_rst_en,
                'description': 'Enable BATFET full system reset' if batfet_rst_en == 1 else 'Disable BATFET full system reset (default)'
            },
            'VDPM_TRACK': {
                'value': vdpm_track,
                'binary': f'{vdpm_track:02b}',
                'description': vdpm_track_desc
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器07值时出错: {e}")
        return None

def parse_reg08(value):
    """解析cx2560x的08寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        vbus_stat2 = (value >> 7) & 0x1     # bit 7: VBUS_STAT[2]
        vbus_stat1 = (value >> 6) & 0x1     # bit 6: VBUS_STAT[1]
        vbus_stat0 = (value >> 5) & 0x1     # bit 5: VBUS_STAT[0]
        chrg_stat1 = (value >> 4) & 0x1     # bit 4: CHRG_STAT[1]
        chrg_stat0 = (value >> 3) & 0x1     # bit 3: CHRG_STAT[0]
        pg_stat = (value >> 2) & 0x1        # bit 2: PG_STAT
        therm_stat = (value >> 1) & 0x1     # bit 1: THERM_STAT
        vsys_stat = value & 0x1             # bit 0: VSYS_STAT
        
        # 组合VBUS_STAT[2:0]和CHRG_STAT[1:0]位
        vbus_stat = (vbus_stat2 << 2) | (vbus_stat1 << 1) | vbus_stat0
        chrg_stat = (chrg_stat1 << 1) | chrg_stat0
        
        # 解析VBUS状态
        vbus_stat_desc = {
            0: "No Input",
            1: "USB Host SDP (500mA)",
            2: "USB CDP (1.5A)",
            3: "USB DCP (2.4A)",
            5: "Unknown Adapter (500mA)",
            6: "Non-Standard Adapter (1A/2A/2.1A/2.4A)",
            7: "OTG"
        }.get(vbus_stat, "Unknown")
        
        # 解析充电状态
        chrg_stat_desc = {
            0: "Not in Charging",
            1: "Pre-Charge (<VBATLOW)",
            2: "Fast Charge",
            3: "Charge Termination Done"
        }.get(chrg_stat, "Unknown")
        
        result = {
            'VBUS_STAT': {
                'value': vbus_stat,
                'binary': f'{vbus_stat:03b}',
                'description': vbus_stat_desc
            },
            'CHRG_STAT': {
                'value': chrg_stat,
                'binary': f'{chrg_stat:02b}',
                'description': chrg_stat_desc
            },
            'PG_STAT': {
                'value': pg_stat,
                'description': 'Power Good' if pg_stat == 1 else 'Not Power Good'
            },
            'THERM_STAT': {
                'value': therm_stat,
                'description': 'In Thermal Regulation' if therm_stat == 1 else 'Normal'
            },
            'VSYS_STAT': {
                'value': vsys_stat,
                'description': 'In VSYSMIN regulation (BAT<VSYSMIN)' if vsys_stat == 1 else 'Not in VSYSMIN regulation (BAT>VSYSMIN)'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器08值时出错: {e}")
        return None

def parse_reg09(value):
    """解析cx2560x的09寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        fault_wdt = (value >> 7) & 0x1      # bit 7: FAULT_WDT
        fault_boost = (value >> 6) & 0x1     # bit 6: FAULT_BOOST
        fault_chrg = (value >> 5) & 0x1      # bit 5: FAULT_CHRG
        fault_bat = (value >> 4) & 0x1       # bit 4: FAULT_BAT
        fault_ntc = (value >> 3) & 0x1       # bit 3: FAULT_NTC
        reserved = value & 0x07              # bits [2:0]: Reserved
        
        result = {
            'FAULT_WDT': {
                'value': fault_wdt,
                'description': 'Watchdog Timer Expiration' if fault_wdt == 1 else 'Normal'
            },
            'FAULT_BOOST': {
                'value': fault_boost,
                'description': 'Boost Mode Fault' if fault_boost == 1 else 'Normal'
            },
            'FAULT_CHRG': {
                'value': fault_chrg,
                'description': 'Charge Fault' if fault_chrg == 1 else 'Normal'
            },
            'FAULT_BAT': {
                'value': fault_bat,
                'description': 'Battery Fault' if fault_bat == 1 else 'Normal'
            },
            'FAULT_NTC': {
                'value': fault_ntc,
                'description': 'NTC Fault' if fault_ntc == 1 else 'Normal'
            },
            'Reserved': {
                'value': reserved,
                'description': 'Reserved bits'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器09值时出错: {e}")
        return None

def parse_reg0A(value):
    """解析cx2560x的0A寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        vbus_gd = (value >> 7) & 0x1       # bit 7: VBUS_GD
        vdpm_stat = (value >> 6) & 0x1     # bit 6: VDPM_STAT
        idpm_stat = (value >> 5) & 0x1     # bit 5: IDPM_STAT
        reserved2 = (value >> 4) & 0x1     # bit 4: Reserved
        reserved1 = (value >> 3) & 0x1     # bit 3: Reserved
        acov_stat = (value >> 2) & 0x1     # bit 2: ACOV_STAT
        vindpm_stat = (value >> 1) & 0x1   # bit 1: VINDPM_STAT
        iindpm_stat = value & 0x1          # bit 0: IINDPM_STAT
        
        result = {
            'VBUS_GD': {
                'value': vbus_gd,
                'description': 'VBUS Good' if vbus_gd == 1 else 'VBUS not Good'
            },
            'VDPM_STAT': {
                'value': vdpm_stat,
                'description': 'In DPM Mode' if vdpm_stat == 1 else 'Not in DPM Mode'
            },
            'IDPM_STAT': {
                'value': idpm_stat,
                'description': 'In DPM Mode' if idpm_stat == 1 else 'Not in DPM Mode'
            },
            'Reserved2': {
                'value': reserved2,
                'description': 'Reserved bit'
            },
            'Reserved1': {
                'value': reserved1,
                'description': 'Reserved bit'
            },
            'ACOV_STAT': {
                'value': acov_stat,
                'description': 'ACOV (Input > VACOV)' if acov_stat == 1 else 'Normal'
            },
            'VINDPM_STAT': {
                'value': vindpm_stat,
                'description': 'In VINDPM Mode' if vindpm_stat == 1 else 'Not in VINDPM Mode'
            },
            'IINDPM_STAT': {
                'value': iindpm_stat,
                'description': 'In IINDPM Mode' if iindpm_stat == 1 else 'Not in IINDPM Mode'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器0A值时出错: {e}")
        return None

def display_reg0A_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器0A的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2]} {binary_value[3]} {binary_value[4]} {binary_value[5]} {binary_value[6]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x0A 解析结果:{Colors.END}" if use_colors else "寄存器 0x0A 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │ │ │ │ │ └─ IINDPM_STAT{end}")
    output.write(f"{cyan}        │ │ │ │ │ │ └─── VINDPM_STAT{end}")
    output.write(f"{cyan}        │ │ │ │ │ └───── ACOV_STAT{end}")
    output.write(f"{cyan}        │ │ │ │ └─────── Reserved{end}")
    output.write(f"{cyan}        │ │ │ └───────── Reserved{end}")
    output.write(f"{cyan}        │ │ └─────────── IDPM_STAT{end}")
    output.write(f"{cyan}        │ └───────────── VDPM_STAT{end}")
    output.write(f"{cyan}        └─────────────── VBUS_GD{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  VBUS_GD: {result['VBUS_GD']['description']}")
    output.write(f"  VDPM_STAT: {result['VDPM_STAT']['description']}")
    output.write(f"  IDPM_STAT: {result['IDPM_STAT']['description']}")
    output.write(f"  Reserved: {result['Reserved2']['description']}, {result['Reserved1']['description']}")
    output.write(f"  ACOV_STAT: {result['ACOV_STAT']['description']}")
    output.write(f"  VINDPM_STAT: {result['VINDPM_STAT']['description']}")
    output.write(f"  IINDPM_STAT: {result['IINDPM_STAT']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - VBUS_GD: VBUS电压状态")
    output.write("    * 0 = VBUS电压不在有效范围")
    output.write("    * 1 = VBUS电压在有效范围内")
    output.write("  - VDPM_STAT: 电压动态功率管理状态")
    output.write("    * 0 = 不在DPM模式")
    output.write("    * 1 = 在DPM模式")
    output.write("  - IDPM_STAT: 电流动态功率管理状态")
    output.write("    * 0 = 不在DPM模式")
    output.write("    * 1 = 在DPM模式")
    output.write("  - ACOV_STAT: 输入过压状态")
    output.write("    * 0 = 正常")
    output.write("    * 1 = 输入电压高于VACOV阈值")
    output.write("  - VINDPM_STAT: 输入电压DPM状态")
    output.write("    * 0 = 不在VINDPM模式")
    output.write("    * 1 = 在VINDPM模式")
    output.write("  - IINDPM_STAT: 输入电流DPM状态")
    output.write("    * 0 = 不在IINDPM模式")
    output.write("    * 1 = 在IINDPM模式")

def display_reg0A_info(reg_value, result, log_line):
    """显示寄存器0A的解析信息"""
    output = OutputCapture()
    display_reg0A_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

class OutputCapture:
    """捕获打印输出的类"""
    def __init__(self):
        self.content = []
    
    def write(self, text):
        print(text)
        self.content.append(text)
    
    def get_content(self):
        return '\n'.join(self.content)

def display_reg00_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器00的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2]} {binary_value[3:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x00 解析结果:{Colors.END}" if use_colors else "寄存器 0x00 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │ └─ IINDPM[4:0]{end}")
    output.write(f"{cyan}        │ │ └─── STAT_DIS{end}")
    output.write(f"{cyan}        │ └───── DPDM_DIS{end}")
    output.write(f"{cyan}        └─────── EN_HIZ{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  EN_HIZ (bit 7): {result['EN_HIZ']['description']}")
    output.write(f"  DPDM_DIS (bit 6): {result['DPDM_DIS']['description']}")
    output.write(f"  STAT_DIS (bit 5): {result['STAT_DIS']['description']}")
    output.write(f"  IINDPM (bits [4:0]): {result['IINDPM']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - IINDPM位设置输入电流限制，范围100mA-3.2A")
    output.write("  - USB SDP = 500mA")
    output.write("  - USB DCP = 2.4A")
    output.write("  - Unknown Adapter = 500mA")
    output.write("  - Non-Standard Adapter = 1A/2A/2.1A/2.4A")

def display_reg01_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器01的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2]} {binary_value[3]} {binary_value[4:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x01 解析结果:{Colors.END}" if use_colors else "寄存器 0x01 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │ │ └─ SYS_MIN[3:0]{end}")
    output.write(f"{cyan}        │ │ │ └─── CHG_CONFIG{end}")
    output.write(f"{cyan}        │ │ └───── OTG_CONFIG{end}")
    output.write(f"{cyan}        │ └─────── WD_RST{end}")
    output.write(f"{cyan}        └───────── Reserved{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  Reserved (bit 7): {result['Reserved']['description']}")
    output.write(f"  WD_RST (bit 6): {result['WD_RST']['description']}")
    output.write(f"  OTG_CONFIG (bit 5): {result['OTG_CONFIG']['description']}")
    output.write(f"  CHG_CONFIG (bit 4): {result['CHG_CONFIG']['description']}")
    output.write(f"  SYS_MIN (bits [3:0]): {result['SYS_MIN']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - WD_RST: I2C看门狗定时器复位")
    output.write("  - OTG_CONFIG: Boost (OTG) 模式配置")
    output.write("  - CHG_CONFIG: 充电使能配置")
    output.write("  - SYS_MIN: 系统最小电压设置")
    output.write("    * 000: 2.6V    001: 2.8V    010: 3.0V    011: 3.2V")
    output.write("    * 100: 3.4V    101: 3.5V    110: 3.6V    111: 3.7V")
    output.write("    * 默认值: 3.5V (101)")

def display_reg02_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器02的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x02 解析结果:{Colors.END}" if use_colors else "寄存器 0x02 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ └─ ICHG[5:0]{end}")
    output.write(f"{cyan}        │ └─── Q1_FULLON{end}")
    output.write(f"{cyan}        └───── BOOST_LIM{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  BOOST_LIM (bit 7): {result['BOOST_LIM']['description']}")
    output.write(f"  Q1_FULLON (bit 6): {result['Q1_FULLON']['description']}")
    output.write(f"  ICHG[5:0]: {result['ICHG']['description']}")
    output.write(f"            二进制值: {result['ICHG']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - BOOST_LIM: Boost Mode Current Limit")
    output.write("    * 0 = 0.5A")
    output.write("    * 1 = 1.2A (default)")
    output.write("  - Q1_FULLON: Q1 MOSFET 控制模式")
    output.write("    * 0 = 在IINDPM<700mA时使用更高的Q1 Rdson (默认，更好的精度)")
    output.write("    * 1 = 始终使用更低的Q1 Rdson (更好的效率)")
    output.write("  - ICHG[5:0]: 快速充电电流设置")
    output.write("    * 范围: 0mA(000000) ~ 3047.5mA(110101)")
    output.write("    * 步进:")
    output.write("      - 000000~001101: 0mA~1170mA, 90mA per step")
    output.write("      - 001110~110101: 805mA~3047.5mA, 57.5mA per step")
    output.write("    * 默认值: 1955mA (100010)")

def display_reg03_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器03的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0:4]} {binary_value[4:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x03 解析结果:{Colors.END}" if use_colors else "寄存器 0x03 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │    └─ ITERM[3:0]{end}")
    output.write(f"{cyan}        └─── IPRECHG[3:0]{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  IPRECHG[3:0]: {result['IPRECHG']['description']}")
    output.write(f"    二进制值: {result['IPRECHG']['binary']}")
    output.write(f"  ITERM[3:0]: {result['ITERM']['description']}")
    output.write(f"    二进制值: {result['ITERM']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - IPRECHG: 预充电电流设置")
    output.write("    * 偏移值: 52mA")
    output.write("    * 步进值: 52mA/step")
    output.write("    * 默认值: 156mA (0010)")
    output.write("    * 注意: IPRECHG > 676mA时限制为676mA (1100)")
    output.write("  - ITERM: 充电终止电流设置")
    output.write("    * 偏移值: 60mA")
    output.write("    * 步进值: 60mA/step")
    output.write("    * 默认值: 180mA (0010)")
    output.write("    * 注意: ITERM > 780mA时限制为780mA (1100)")

def display_reg04_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器04的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0:5]} {binary_value[5:7]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x04 解析结果:{Colors.END}" if use_colors else "寄存器 0x04 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │    │ └─ VRECHG{end}")
    output.write(f"{cyan}        │    └─── Reserved[1:0]{end}")
    output.write(f"{cyan}        └─────── VREG[4:0]{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  VREG[4:0]: {result['VREG']['description']}")
    output.write(f"    二进制值: {result['VREG']['binary']}")
    output.write(f"    电压值: {result['VREG']['voltage']}")
    output.write(f"  Reserved[1:0]: {result['Reserved']['description']}")
    output.write(f"  VRECHG: {result['VRECHG']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - VREG: 充电电压设置")
    output.write("    * 偏移值: 3.856V")
    output.write("    * 步进值: 32mV/step")
    output.write("    * 范围: 3.856V~4.624V")
    output.write("    * 默认值: 4.208V (01011)")
    output.write("  - VRECHG: 充电电压调节")
    output.write("    * 0 = 4.3V (default)")
    output.write("    * 1 = 4.1V")

def display_reg05_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器05的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2:4]} {binary_value[4]} {binary_value[5]} {binary_value[6]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x05 解析结果:{Colors.END}" if use_colors else "寄存器 0x05 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │  │ │ │ └─ JEITA_ISET{end}")
    output.write(f"{cyan}        │ │ │  │ │ └─── TREG[0]{end}")
    output.write(f"{cyan}        │ │ │  │ └───── CHG_TIMER{end}")
    output.write(f"{cyan}        │ │ │  └─────── EN_TIMER{end}")
    output.write(f"{cyan}        │ │ └────────── WATCHDOG[1:0]{end}")
    output.write(f"{cyan}        │ └──────────── Reserved{end}")
    output.write(f"{cyan}        └────────────── EN_TERM{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  EN_TERM (bit 7): {result['EN_TERM']['description']}")
    output.write(f"  Reserved (bit 6): {result['Reserved']['description']}")
    output.write(f"  WATCHDOG[1:0]: {result['WATCHDOG']['description']}")
    output.write(f"    二进制值: {result['WATCHDOG']['binary']}")
    output.write(f"  EN_TIMER (bit 3): {result['EN_TIMER']['description']}")
    output.write(f"  CHG_TIMER (bit 2): {result['CHG_TIMER']['description']}")
    output.write(f"  TREG[0] (bit 1): {result['TREG']['description']}")
    output.write(f"  JEITA_ISET (bit 0): {result['JEITA_ISET']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - EN_TERM: 充电终止使能")
    output.write("    * 0 = Disable")
    output.write("    * 1 = Enable (default)")
    output.write("  - WATCHDOG: I2C看门狗定时器设置")
    output.write("    * 00 = Disable watchdog timer")
    output.write("    * 01 = 40s (default)")
    output.write("    * 10 = 80s")
    output.write("    * 11 = 160s")
    output.write("  - EN_TIMER: 充电安全定时器使能")
    output.write("    * 0 = Disable")
    output.write("    * 1 = Enable (default)")
    output.write("  - CHG_TIMER: 快速充电定时器设置")
    output.write("    * 0 = 5hrs")
    output.write("    * 1 = 10hrs (default)")
    output.write("  - TREG[0]: 温度调节阈值")
    output.write("    * 0 = 100°C")
    output.write("    * 1 = 120°C (default)")

def display_reg06_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器06的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0:2]} {binary_value[2:4]} {binary_value[4:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x06 解析结果:{Colors.END}" if use_colors else "寄存器 0x06 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │  │  └─ VINDPM[3:0]{end}")
    output.write(f"{cyan}        │  └─── BOOSTV[1:0]{end}")
    output.write(f"{cyan}        └────── OVP[1:0]{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  OVP[1:0]: {result['OVP']['description']}")
    output.write(f"    二进制值: {result['OVP']['binary']}")
    output.write(f"  BOOSTV[1:0]: {result['BOOSTV']['description']}")
    output.write(f"    二进制值: {result['BOOSTV']['binary']}")
    output.write(f"  VINDPM[3:0]: {result['VINDPM']['description']}")
    output.write(f"    二进制值: {result['VINDPM']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - OVP[1:0]: ACOV阈值设置")
    output.write("    * 00 = 5.5V")
    output.write("    * 01 = 6.5V (5V input, default)")
    output.write("    * 10 = 10.5V (9V input)")
    output.write("    * 11 = 14V (12V input)")
    output.write("  - BOOSTV[1:0]: Boost模式电压调节")
    output.write("    * 偏移值: 4.87V")
    output.write("    * 范围: 4.87V - 5.254V")
    output.write("    * 步进: 128mV")
    output.write("    * 默认值: 5.126V (10)")
    output.write("  - VINDPM[3:0]: 输入电压动态功率管理阈值")
    output.write("    * 偏移值: 3.9V")
    output.write("    * 范围: 3.9V (0000) - 5.4V (1111)")
    output.write("    * 步进: 100mV")
    output.write("    * 默认值: 4.5V (0110)")

def display_reg07_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器07的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2]} {binary_value[3]} {binary_value[4]} {binary_value[5]} {binary_value[6]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x07 解析结果:{Colors.END}" if use_colors else "寄存器 0x07 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │ │ │ │ │ └─ VDPM_TRACK[1:0]{end}")
    output.write(f"{cyan}        │ │ │ │ │ │ └─── BATFET_RST_EN{end}")
    output.write(f"{cyan}        │ │ │ │ │ └─── BATFET_DLY{end}")
    output.write(f"{cyan}        │ │ │ │ └─── JEITA_VSET{end}")
    output.write(f"{cyan}        │ │ │ └─── BATFET_DIS{end}")
    output.write(f"{cyan}        │ │ └─── TMR2X_EN{end}")
    output.write(f"{cyan}        │ └─── IINDET_EN{end}")
    output.write(f"{cyan}        └────── VDPM_TRACK[1:0]{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  IINDET_EN (bit 7): {result['IINDET_EN']['description']}")
    output.write(f"  TMR2X_EN (bit 6): {result['TMR2X_EN']['description']}")
    output.write(f"  BATFET_DIS (bit 5): {result['BATFET_DIS']['description']}")
    output.write(f"  JEITA_VSET (bit 4): {result['JEITA_VSET']['description']}")
    output.write(f"  BATFET_DLY (bit 3): {result['BATFET_DLY']['description']}")
    output.write(f"  BATFET_RST_EN (bit 2): {result['BATFET_RST_EN']['description']}")
    output.write(f"  VDPM_TRACK[1:0]: {result['VDPM_TRACK']['description']}")
    output.write(f"    二进制值: {result['VDPM_TRACK']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - IINDET_EN: 强制D+/D-检测")
    output.write("    * 0 = 不强制检测")
    output.write("    * 1 = 强制检测")
    output.write("  - TMR2X_EN: 输入DPM或热调节期间安全定时器慢速")
    output.write("    * 0 = 输入DPM或热调节期间安全定时器不慢速")
    output.write("    * 1 = 输入DPM或热调节期间安全定时器慢速")
    output.write("  - BATFET_DIS: 强制BATFET关闭")
    output.write("    * 0 = 允许BATFET打开")
    output.write("    * 1 = 强制BATFET关闭")
    output.write("  - JEITA_VSET: 在JEITA高温期间将充电电压设置为VREG")
    output.write("    * 0 = 在JEITA高温期间将充电电压设置为VREG-200mV")
    output.write("    * 1 = 在JEITA高温期间将充电电压设置为VREG")
    output.write("  - BATFET_DLY: BATFET关闭延迟")
    output.write("    * 0 = 当BATFET_DIS位设置时，BATFET关闭延迟")
    output.write("    * 1 = 当BATFET_DIS位设置时，BATFET立即关闭")
    output.write("  - BATFET_RST_EN: 启用BATFET系统复位")
    output.write("    * 0 = 禁用BATFET系统复位")
    output.write("    * 1 = 启用BATFET系统复位")
    output.write("  - VDPM_TRACK[1:0]: VDPM跟踪设置")
    output.write("    * 00 = 禁用跟踪功能（VINDPM由寄存器设置）")
    output.write("    * 01 = VBAT + 200mV")
    output.write("    * 10 = VBAT + 250mV")
    output.write("    * 11 = 保留")

def display_reg08_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器08的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0:3]} {binary_value[3:5]} {binary_value[5]} {binary_value[6]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x08 解析结果:{Colors.END}" if use_colors else "寄存器 0x08 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │   │  │  │  └─ VSYS_STAT{end}")
    output.write(f"{cyan}        │   │  │  └─── THERM_STAT{end}")
    output.write(f"{cyan}        │   │  └───── PG_STAT{end}")
    output.write(f"{cyan}        │   └─────── CHRG_STAT[1:0]{end}")
    output.write(f"{cyan}        └─────────── VBUS_STAT[2:0]{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  VBUS_STAT[2:0]: {result['VBUS_STAT']['description']}")
    output.write(f"    二进制值: {result['VBUS_STAT']['binary']}")
    output.write(f"  CHRG_STAT[1:0]: {result['CHRG_STAT']['description']}")
    output.write(f"    二进制值: {result['CHRG_STAT']['binary']}")
    output.write(f"  PG_STAT: {result['PG_STAT']['description']}")
    output.write(f"  THERM_STAT: {result['THERM_STAT']['description']}")
    output.write(f"  VSYS_STAT: {result['VSYS_STAT']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - VBUS_STAT[2:0]: VBUS状态")
    output.write("    * 000 = No Input")
    output.write("    * 001 = USB Host SDP (500mA)")
    output.write("    * 010 = USB CDP (1.5A)")
    output.write("    * 011 = USB DCP (2.4A)")
    output.write("    * 101 = Unknown Adapter (500mA)")
    output.write("    * 110 = Non-Standard Adapter (1A/2A/2.1A/2.4A)")
    output.write("    * 111 = OTG")
    output.write("  - CHRG_STAT[1:0]: 充电状态")
    output.write("    * 00 = Not in Charging")
    output.write("    * 01 = Pre-Charge (<VBATLOW)")
    output.write("    * 10 = Fast Charge")
    output.write("    * 11 = Charge Termination Done")
    output.write("  - PG_STAT: Power Good状态")
    output.write("  - THERM_STAT: 热调节状态")
    output.write("  - VSYS_STAT: VSYS调节状态")

def display_reg09_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器09的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2]} {binary_value[3]} {binary_value[4]} {binary_value[5:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x09 解析结果:{Colors.END}" if use_colors else "寄存器 0x09 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │ │ │ └─ Reserved[2:0]{end}")
    output.write(f"{cyan}        │ │ │ │ └─── FAULT_NTC{end}")
    output.write(f"{cyan}        │ │ │ └───── FAULT_BAT{end}")
    output.write(f"{cyan}        │ │ └─────── FAULT_CHRG{end}")
    output.write(f"{cyan}        │ └───────── FAULT_BOOST{end}")
    output.write(f"{cyan}        └─────────── FAULT_WDT{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  FAULT_WDT: {result['FAULT_WDT']['description']}")
    output.write(f"  FAULT_BOOST: {result['FAULT_BOOST']['description']}")
    output.write(f"  FAULT_CHRG: {result['FAULT_CHRG']['description']}")
    output.write(f"  FAULT_BAT: {result['FAULT_BAT']['description']}")
    output.write(f"  FAULT_NTC: {result['FAULT_NTC']['description']}")
    output.write(f"  Reserved[2:0]: {result['Reserved']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - FAULT_WDT: 看门狗定时器超时故障")
    output.write("    * 0 = 正常")
    output.write("    * 1 = 看门狗定时器超时")
    output.write("  - FAULT_BOOST: Boost模式故障")
    output.write("    * 0 = 正常")
    output.write("    * 1 = Boost模式故障")
    output.write("  - FAULT_CHRG: 充电故障")
    output.write("    * 0 = 正常")
    output.write("    * 1 = 充电故障")
    output.write("  - FAULT_BAT: 电池故障")
    output.write("    * 0 = 正常")
    output.write("    * 1 = 电池故障")
    output.write("  - FAULT_NTC: NTC故障")
    output.write("    * 0 = 正常")
    output.write("    * 1 = NTC故障")

def display_reg09_info(reg_value, result, log_line):
    """显示寄存器09的解析信息"""
    output = OutputCapture()
    display_reg09_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg08_info(reg_value, result, log_line):
    """显示寄存器08的解析信息"""
    output = OutputCapture()
    display_reg08_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg00_info(reg_value, result, log_line):
    """显示寄存器00的解析信息"""
    output = OutputCapture()
    display_reg00_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg01_info(reg_value, result, log_line):
    """显示寄存器01的解析信息"""
    output = OutputCapture()
    display_reg01_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg02_info(reg_value, result, log_line):
    """显示寄存器02的解析信息"""
    output = OutputCapture()
    display_reg02_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg03_info(reg_value, result, log_line):
    """显示寄存器03的解析信息"""
    output = OutputCapture()
    display_reg03_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg04_info(reg_value, result, log_line):
    """显示寄存器04的解析信息"""
    output = OutputCapture()
    display_reg04_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg05_info(reg_value, result, log_line):
    """显示寄存器05的解析信息"""
    output = OutputCapture()
    display_reg05_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg06_info(reg_value, result, log_line):
    """显示寄存器06的解析信息"""
    output = OutputCapture()
    display_reg06_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def display_reg07_info(reg_value, result, log_line):
    """显示寄存器07的解析信息"""
    output = OutputCapture()
    display_reg07_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def create_output_directory():
    """创建输出目录"""
    output_dir = 'cx2560x'
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def get_output_filename():
    """生成带时间戳的输出文件名"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"registers_{timestamp}.txt"

def write_to_file(content, output_dir, filename, mode='a'):
    """将内容写入文件"""
    filepath = os.path.join(output_dir, filename)
    with open(filepath, mode, encoding='utf-8') as f:
        f.write(content)
        f.write('\n' + '='*80 + '\n')  # 添加分隔线
    if mode == 'w':  # 只在创建新文件时打印路径
        print(f"结果将保存到: {filepath}")

def check_cx2560x_ic(log_file):
    """检查是否使用cx2560x充电IC"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'cx2560x_init' in line:
                    return True
        return False
    except Exception as e:
        print(f"检查cx2560x充电IC时出错: {e}")
        return False

def parse_cx2560x_registers(log_file):
    """解析cx2560x充电IC的寄存器信息"""
    print("\n开始解析cx2560x充电IC寄存器...")
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                # 使用parse_register函数统一处理所有寄存器
                match = re.search(r'\[REG_0x([0-9a-fA-F]{2})\]=0x([0-9a-fA-F]{2})', line)
                if match:
                    reg = match.group(1)
                    value = match.group(2)
                    parse_func, display_func = parse_register(reg, value)
                    if parse_func and display_func:
                        result = parse_func(value)
                        if result:
                            display_func(value, result, line.strip())
    except Exception as e:
        print(f"解析cx2560x寄存器时出错: {e}")

def process_cx2560x(log_file=None):
    """处理cx2560x充电IC相关的功能"""
    print("请输入要解析的寄存器信息，格式如下：")
    print("REG_0x00=0x04 REG_0x01=0x1a REG_0x02=0xa2 REG_0x03=0x12 ...")
    print("输入 'q' 退出")
    
    # 创建输出目录和文件
    output_dir = create_output_directory()
    output_file = get_output_filename()
    # 写入文件头
    write_to_file(f"cx2560x寄存器解析结果\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 
                 output_dir, output_file, 'w')
    
    while True:
        try:
            user_input = input("\n请输入寄存器信息: ").strip()
            
            if user_input.lower() == 'q':
                break
            
            # 使用正则表达式匹配所有寄存器值
            matches = re.finditer(r'\[?REG_0x([0-9a-fA-F]{2})\]?=0x([0-9a-fA-F]{2})', user_input)
            found = False
            
            for match in matches:
                found = True
                reg = match.group(1)
                value = match.group(2)
                
                print(f"\n解析寄存器 0x{reg} = 0x{value}")
                
                if reg == '00':
                    result = parse_reg00(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg00_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg00_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '01':
                    result = parse_reg01(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg01_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg01_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '02':
                    result = parse_reg02(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg02_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg02_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '03':
                    result = parse_reg03(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg03_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg03_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '04':
                    result = parse_reg04(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg04_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg04_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '05':
                    result = parse_reg05(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg05_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg05_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '06':
                    result = parse_reg06(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg06_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg06_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '07':
                    result = parse_reg07(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg07_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg07_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '08':
                    result = parse_reg08(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg08_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg08_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '09':
                    result = parse_reg09(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg09_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg09_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '0a':
                    result = parse_reg0A(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg0A_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg0A_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '0b':
                    result = parse_reg0B(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg0B_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg0B_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '0c':
                    result = parse_reg0C(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg0C_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg0C_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '0d':
                    result = parse_reg0D(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg0D_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg0D_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                elif reg == '0e':
                    result = parse_reg0E(value)
                    if result:
                        # 控制台输出带颜色
                        output = OutputCapture()
                        display_reg0E_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=True)
                        print(output.get_content())
                        # 文件写入不带颜色
                        output = OutputCapture()
                        display_reg0E_info_to_output(value, result, f"用户输入: REG_0x{reg}=0x{value}", output, use_colors=False)
                        write_to_file(output.get_content(), output_dir, output_file)
                else:
                    print(f"暂不支持解析寄存器 0x{reg}")
            
            if not found:
                print("输入格式错误，请使用正确的格式，例如：")
                print("REG_0x00=0x04 REG_0x01=0x1a REG_0x02=0xa2 REG_0x03=0x12")
                
        except Exception as e:
            print(f"解析输入时出错: {e}")

def parse_register(reg, value):
    """根据寄存器地址解析寄存器值
    
    Args:
        reg: 寄存器地址
        value: 寄存器值(16进制字符串)
    
    Returns:
        解析结果字典
    """
    reg = reg.lower()
    parse_functions = {
        "00": parse_reg00,
        "01": parse_reg01,
        "02": parse_reg02,
        "03": parse_reg03,
        "04": parse_reg04,
        "05": parse_reg05,
        "06": parse_reg06,
        "07": parse_reg07,
        "08": parse_reg08,
        "09": parse_reg09,
        "0a": parse_reg0A,
        "0b": parse_reg0B,
        "0c": parse_reg0C,
        "0d": parse_reg0D,
        "0e": parse_reg0E
    }
    
    display_functions = {
        "00": display_reg00_info,
        "01": display_reg01_info,
        "02": display_reg02_info,
        "03": display_reg03_info,
        "04": display_reg04_info,
        "05": display_reg05_info,
        "06": display_reg06_info,
        "07": display_reg07_info,
        "08": display_reg08_info,
        "09": display_reg09_info,
        "0a": display_reg0A_info,
        "0b": display_reg0B_info,
        "0c": display_reg0C_info,
        "0d": display_reg0D_info,
        "0e": display_reg0E_info
    }
    
    if reg in parse_functions:
        return parse_functions[reg], display_functions[reg]
    else:
        return None, None

def parse_reg0B(value):
    """解析cx2560x的0B寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        reg_rst = (value >> 7) & 0x1       # bit 7: REG_RST
        pn3 = (value >> 6) & 0x1           # bit 6: PN[3]
        pn2 = (value >> 5) & 0x1           # bit 5: PN[2]
        pn1 = (value >> 4) & 0x1           # bit 4: PN[1]
        pn0 = (value >> 3) & 0x1           # bit 3: PN[0]
        reserved = (value >> 2) & 0x1       # bit 2: Reserved
        dev_rev1 = (value >> 1) & 0x1      # bit 1: DEV_REV[1]
        dev_rev0 = value & 0x1             # bit 0: DEV_REV[0]
        
        # 组合PN[3:0]位
        pn = (pn3 << 3) | (pn2 << 2) | (pn1 << 1) | pn0
        
        # 组合DEV_REV[1:0]位
        dev_rev = (dev_rev1 << 1) | dev_rev0
        
        result = {
            'REG_RST': {
                'value': reg_rst,
                'description': 'Reset to default register value and reset safety timer' if reg_rst == 1 else 'Keep current register setting'
            },
            'PN': {
                'value': pn,
                'binary': f'{pn:04b}',
                'description': f'Part Number: 0x{pn:X}'
            },
            'Reserved': {
                'value': reserved,
                'description': 'Reserved bit'
            },
            'DEV_REV': {
                'value': dev_rev,
                'binary': f'{dev_rev:02b}',
                'description': f'Device Revision: 0x{dev_rev:X}'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器0B值时出错: {e}")
        return None

def display_reg0B_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器0B的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1:5]} {binary_value[5]} {binary_value[6:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x0B 解析结果:{Colors.END}" if use_colors else "寄存器 0x0B 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │    │ └─ DEV_REV[1:0]{end}")
    output.write(f"{cyan}        │ │    └─── Reserved{end}")
    output.write(f"{cyan}        │ └──────── PN[3:0]{end}")
    output.write(f"{cyan}        └────────── REG_RST{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  REG_RST: {result['REG_RST']['description']}")
    output.write(f"  PN[3:0]: {result['PN']['description']}")
    output.write(f"    二进制值: {result['PN']['binary']}")
    output.write(f"  Reserved: {result['Reserved']['description']}")
    output.write(f"  DEV_REV[1:0]: {result['DEV_REV']['description']}")
    output.write(f"    二进制值: {result['DEV_REV']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - REG_RST: 寄存器复位控制")
    output.write("    * 0 = 保持当前寄存器设置")
    output.write("    * 1 = 复位到默认寄存器值并复位安全定时器")
    output.write("    注意: 位在寄存器复位完成后自动复位为0")
    output.write("  - PN[3:0]: 芯片型号")
    output.write("  - DEV_REV[1:0]: 设备版本号")

def display_reg0B_info(reg_value, result, log_line):
    """显示寄存器0B的解析信息"""
    output = OutputCapture()
    display_reg0B_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def parse_reg0C(value):
    """解析cx2560x的0C寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        boost_freq = (value >> 7) & 0x1     # bit 7: BOOST_FREQ
        bcold = (value >> 6) & 0x1          # bit 6: BCOLD
        bhot1 = (value >> 5) & 0x1          # bit 5: BHOT[1]
        bhot0 = (value >> 4) & 0x1          # bit 4: BHOT[0]
        reserved3 = (value >> 3) & 0x1      # bit 3: Reserved
        reserved2 = (value >> 2) & 0x1      # bit 2: Reserved
        reserved1 = (value >> 1) & 0x1      # bit 1: Reserved
        ico_en = value & 0x1                # bit 0: ICO_EN
        
        # 组合BHOT[1:0]位
        bhot = (bhot1 << 1) | bhot0
        
        # 解析BHOT温度阈值
        bhot_desc = {
            0: "VBHOT1 Threshold (94.75%, 60°C)",
            1: "VBHOT2 Threshold (97.75%, 55°C)",
            2: "VBHOT3 Threshold (81.25%, 65°C) (default)",
            3: "Disable boost mode thermal protection"
        }.get(bhot, "Unknown")
        
        result = {
            'BOOST_FREQ': {
                'value': boost_freq,
                'description': '500kHz' if boost_freq == 1 else '1.5MHz (default)'
            },
            'BCOLD': {
                'value': bcold,
                'description': 'VBCOLD2 Threshold (80%, -20°C) (default)' if bcold == 1 else 'VBCOLD1 Threshold (77%, -10°C)'
            },
            'BHOT': {
                'value': bhot,
                'binary': f'{bhot:02b}',
                'description': bhot_desc
            },
            'Reserved': {
                'value': (reserved3 << 2) | (reserved2 << 1) | reserved1,
                'description': 'Reserved bits'
            },
            'ICO_EN': {
                'value': ico_en,
                'description': 'Enable Input Current Optimization' if ico_en == 1 else 'Disable Optimization'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器0C值时出错: {e}")
        return None

def display_reg0C_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器0C的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2:4]} {binary_value[4:7]} {binary_value[7]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x0C 解析结果:{Colors.END}" if use_colors else "寄存器 0x0C 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ │   │ └─ ICO_EN{end}")
    output.write(f"{cyan}        │ │ │   └─── Reserved[2:0]{end}")
    output.write(f"{cyan}        │ │ └─────── BHOT[1:0]{end}")
    output.write(f"{cyan}        │ └───────── BCOLD{end}")
    output.write(f"{cyan}        └─────────── BOOST_FREQ{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  BOOST_FREQ: {result['BOOST_FREQ']['description']}")
    output.write(f"  BCOLD: {result['BCOLD']['description']}")
    output.write(f"  BHOT[1:0]: {result['BHOT']['description']}")
    output.write(f"    二进制值: {result['BHOT']['binary']}")
    output.write(f"  Reserved[2:0]: {result['Reserved']['description']}")
    output.write(f"  ICO_EN: {result['ICO_EN']['description']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - BOOST_FREQ: Boost模式频率选择")
    output.write("    * 0 = 1.5MHz (default)")
    output.write("    * 1 = 500kHz")
    output.write("  - BCOLD: Boost模式冷温度监控阈值")
    output.write("    * 0 = VBCOLD1 Threshold (77%, -10°C)")
    output.write("    * 1 = VBCOLD2 Threshold (80%, -20°C) (default)")
    output.write("  - BHOT[1:0]: Boost模式热温度监控阈值")
    output.write("    * 00 = VBHOT1 Threshold (94.75%, 60°C)")
    output.write("    * 01 = VBHOT2 Threshold (97.75%, 55°C)")
    output.write("    * 10 = VBHOT3 Threshold (81.25%, 65°C) (default)")
    output.write("    * 11 = 禁用boost模式热保护")
    output.write("  - ICO_EN: 输入电流限制优化使能")
    output.write("    * 0 = 禁用优化")
    output.write("    * 1 = 使能优化")

def display_reg0C_info(reg_value, result, log_line):
    """显示寄存器0C的解析信息"""
    output = OutputCapture()
    display_reg0C_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def parse_reg0D(value):
    """解析cx2560x的0D寄存器值"""
    try:
        value = int(value, 16)  # 将16进制字符串转换为整数
        
        # 解析各个位域
        force_ico = (value >> 7) & 0x1      # bit 7: FORCE_ICO
        ico_optimized = (value >> 6) & 0x1   # bit 6: ICO_OPTIMIZED
        idpm_lim5 = (value >> 5) & 0x1      # bit 5: IDPM_LIM[5]
        idpm_lim4 = (value >> 4) & 0x1      # bit 4: IDPM_LIM[4]
        idpm_lim3 = (value >> 3) & 0x1      # bit 3: IDPM_LIM[3]
        idpm_lim2 = (value >> 2) & 0x1      # bit 2: IDPM_LIM[2]
        idpm_lim1 = (value >> 1) & 0x1      # bit 1: IDPM_LIM[1]
        idpm_lim0 = value & 0x1             # bit 0: IDPM_LIM[0]
        
        # 组合IDPM_LIM[5:0]位
        idpm_lim = (idpm_lim5 << 5) | (idpm_lim4 << 4) | (idpm_lim3 << 3) | \
                  (idpm_lim2 << 2) | (idpm_lim1 << 1) | idpm_lim0
        
        # 计算输入电流限制值
        # 偏移值: 100mA
        # 范围: 100mA (000000) - 3.25A (111111)
        current_limit = 100 + (idpm_lim * 50)  # 每步50mA
        
        result = {
            'FORCE_ICO': {
                'value': force_ico,
                'description': 'Force ICO (will back to 0 after ICO starts)' if force_ico == 1 else 'Do not force ICO'
            },
            'ICO_OPTIMIZED': {
                'value': ico_optimized,
                'description': 'Maximum Input Current Detected' if ico_optimized == 1 else 'Optimization is in progress'
            },
            'IDPM_LIM': {
                'value': idpm_lim,
                'binary': f'{idpm_lim:06b}',
                'current': f'{current_limit}mA',
                'description': f'Input Current Limit: {current_limit}mA'
            }
        }
        
        return result
    except Exception as e:
        print(f"解析寄存器0D值时出错: {e}")
        return None

def display_reg0D_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """显示寄存器0D的解析信息到指定输出对象"""
    # 将十六进制值转换为整数，然后转换为8位二进制字符串
    binary_value = format(int(reg_value, 16), '08b')
    # 为了更好的可读性，在二进制字符串中添加分隔符
    binary_formatted = f"{binary_value[0]} {binary_value[1]} {binary_value[2:8]}"
    
    # 根据是否使用颜色来格式化输出
    header = f"{Colors.HEADER}{Colors.BOLD}寄存器 0x0D 解析结果:{Colors.END}" if use_colors else "寄存器 0x0D 解析结果:"
    cyan = Colors.CYAN if use_colors else ""
    end = Colors.END if use_colors else ""
    green = Colors.GREEN if use_colors else ""
    yellow = Colors.YELLOW if use_colors else ""
    
    output.write(f"\n{header}")
    output.write(f"{cyan}原始日志: {log_line}{end}")
    output.write(f"{cyan}原始值: 0x{reg_value}{end}")
    output.write(f"{cyan}二进制: {binary_formatted}  (bit 7 -> bit 0){end}")
    output.write(f"{cyan}        │ │ └─ IDPM_LIM[5:0]{end}")
    output.write(f"{cyan}        │ └─── ICO_OPTIMIZED{end}")
    output.write(f"{cyan}        └───── FORCE_ICO{end}")
    output.write(f"\n{green}各位域含义:{end}")
    output.write(f"  FORCE_ICO: {result['FORCE_ICO']['description']}")
    output.write(f"  ICO_OPTIMIZED: {result['ICO_OPTIMIZED']['description']}")
    output.write(f"  IDPM_LIM[5:0]: {result['IDPM_LIM']['description']}")
    output.write(f"    二进制值: {result['IDPM_LIM']['binary']}")
    output.write(f"\n{yellow}注意事项:{end}")
    output.write("  - FORCE_ICO: 强制启动输入电流优化")
    output.write("    * 0 = 不强制启动ICO")
    output.write("    * 1 = 强制启动ICO (ICO启动后自动清零)")
    output.write("  - ICO_OPTIMIZED: 输入电流优化状态")
    output.write("    * 0 = 优化进行中")
    output.write("    * 1 = 已检测到最大输入电流")
    output.write("  - IDPM_LIM[5:0]: 输入电流限制设置")
    output.write("    * 偏移值: 100mA")
    output.write("    * 步进值: 50mA/step")
    output.write("    * 范围: 100mA (000000) - 3.25A (111111)")
    output.write("    * 典型值:")
    output.write("      - 100mA (000000)")
    output.write("      - 200mA (000010)")
    output.write("      - 400mA (000110)")
    output.write("      - 800mA (001110)")
    output.write("      - 1600mA (011110)")

def display_reg0D_info(reg_value, result, log_line):
    """显示寄存器0D的解析信息"""
    output = OutputCapture()
    display_reg0D_info_to_output(reg_value, result, log_line, output, use_colors=True)
    print(output.get_content())

def parse_reg0E(value):
    """解析0x0E寄存器的值
    
    位域定义:
    - VREG[5:0] (bits 7-2): 充电电压设置
      - 偏移值: 3.856V
      - 步进值: 根据位值计算
      - 范围: 3.856V - 4.624V
    - VREG_FT (bit 1): VREG微调
      - 0: 禁用(默认)
      - 1: VREG+8mV
    - BAT_LOADEN (bit 0): 电池负载使能
      - 0: 禁用
      - 1: 使能
    """
    value = int(value, 16)
    result = {}
    
    # 解析VREG[5:0]位
    vreg_bits = (value >> 2) & 0x3F
    vreg_voltage = 3.856 + (vreg_bits * 0.016)  # 每步16mV
    if vreg_voltage > 4.624:  # 限制最大值
        vreg_voltage = 4.624
    
    vreg_values = {
        7: "512mV",
        6: "256mV",
        5: "128mV",
        4: "64mV",
        3: "32mV",
        2: "16mV"
    }
    
    for bit, mv_value in vreg_values.items():
        bit_value = (value >> bit) & 0x01
        result[f"VREG[{bit}]"] = {
            "value": bit_value,
            "description": f"{mv_value} {'设置' if bit_value else '未设置'}"
        }
    
    # 解析VREG_FT位
    vreg_ft = (value >> 1) & 0x01
    result["VREG_FT"] = {
        "value": vreg_ft,
        "description": "VREG+8mV" if vreg_ft else "禁用(默认)"
    }
    
    # 解析BAT_LOADEN位
    bat_loaden = value & 0x01
    result["BAT_LOADEN"] = {
        "value": bat_loaden,
        "description": "使能" if bat_loaden else "禁用"
    }
    
    # 添加计算得到的充电电压值
    result["VREG_TOTAL"] = {
        "value": vreg_voltage,
        "description": f"充电电压: {vreg_voltage:.3f}V"
    }
    
    return result

def display_reg0E_info_to_output(reg_value, result, log_line, output, use_colors=True):
    """将0x0E寄存器信息格式化输出到指定输出对象"""
    value = int(reg_value, 16)
    
    if use_colors:
        output.write(f"{Colors.HEADER}{log_line}{Colors.END}\n")
        output.write(f"{Colors.BOLD}寄存器值: 0x{reg_value} (0b{value:08b}){Colors.END}\n")
    else:
        output.write(f"{log_line}\n")
        output.write(f"寄存器值: 0x{reg_value} (0b{value:08b})\n")
    
    output.write("\n充电电压设置:\n")
    for i in range(7, 1, -1):
        field_name = f"VREG[{i}]"
        if field_name in result:
            field = result[field_name]
            bit_value = field["value"]
            description = field["description"]
            
            if use_colors:
                color = Colors.GREEN if bit_value else Colors.RED
                output.write(f"  {field_name}: {color}{bit_value}{Colors.END} - {description}\n")
            else:
                output.write(f"  {field_name}: {bit_value} - {description}\n")
    
    # 显示VREG_FT设置
    field = result["VREG_FT"]
    if use_colors:
        color = Colors.GREEN if field["value"] else Colors.RED
        output.write(f"\nVREG微调: {color}{field['value']}{Colors.END} - {field['description']}\n")
    else:
        output.write(f"\nVREG微调: {field['value']} - {field['description']}\n")
    
    # 显示BAT_LOADEN设置
    field = result["BAT_LOADEN"]
    if use_colors:
        color = Colors.GREEN if field["value"] else Colors.RED
        output.write(f"\n电池负载: {color}{field['value']}{Colors.END} - {field['description']}\n")
    else:
        output.write(f"\n电池负载: {field['value']} - {field['description']}\n")
    
    # 显示计算得到的总充电电压
    field = result["VREG_TOTAL"]
    if use_colors:
        output.write(f"\n{Colors.CYAN}{field['description']}{Colors.END}\n")
    else:
        output.write(f"\n{field['description']}\n")
    
    output.write("\n")

def display_reg0E_info(reg_value, result, log_line):
    """显示0x0E寄存器信息的便捷函数"""
    output = OutputCapture()
    display_reg0E_info_to_output(reg_value, result, log_line, output)
    print(output.get_content())
    return output.get_content()

if __name__ == "__main__":
    """主函数入口"""
    import sys
    
    if len(sys.argv) < 1:
        print("用法: python cx2560x.py <log_file>")
        print("  或: python cx2560x.py")
        exit()
    
    if len(sys.argv) == 2:
        # 处理日志文件
        log_file = sys.argv[1]
        if check_cx2560x_ic(log_file):
            parse_cx2560x_registers(log_file)
        else:
            print(f"日志文件 {log_file} 中未检测到cx2560x充电IC")
    else:
        # 交互式模式
        process_cx2560x(None)
