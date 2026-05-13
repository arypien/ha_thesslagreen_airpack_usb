"""Constants for AirPack Home integration."""

DOMAIN = "airpack_home"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_SLAVE = 10
DEFAULT_BAUDRATE = 9600

# ─── Modbus function codes ───────────────────────────────────────────────────
FC_READ_COILS = 1           # 01 READ COILS
FC_READ_DISCRETE = 2        # 02 READ DISCRETE INPUTS
FC_READ_HOLDING = 3         # 03 READ HOLDING REGISTERS
FC_READ_INPUT = 4           # 04 READ INPUT REGISTERS

# ─── 01 READ COILS (register address: hex → dec) ────────────────────────────
COIL_REGISTERS = {
    "duct_water_heater_pump": {"address": 0x0005, "name": "Pompa nagrzewnicy wodnej"},
    "bypass":                 {"address": 0x0009, "name": "Siłownik bypass"},
    "info":                   {"address": 0x000A, "name": "Potwierdzenie pracy centrali (O1)"},
    "power_supply_fans":      {"address": 0x000B, "name": "Zasilanie wentylatorów"},
    "heating_cable":          {"address": 0x000C, "name": "Kabel grzejny"},
    "workt_permit":           {"address": 0x000D, "name": "Potwierdzenie pracy (Expansion)"},
    "gwc":                    {"address": 0x000E, "name": "Przekaźnik GWC"},
    "hood":                   {"address": 0x000F, "name": "Przepustnica okapu"},
}

# ─── 02 READ DISCRETE INPUTS ─────────────────────────────────────────────────
DISCRETE_REGISTERS = {
    "duct_heater_protection": {"address": 0x0000, "name": "Zabezpieczenie termiczne nagrzewnicy"},
    "expansion":              {"address": 0x0001, "name": "Moduł Expansion"},
    "dp_duct_filter_overflow":{"address": 0x0003, "name": "Presostat filtra kanałowego"},
    "hood_input":             {"address": 0x0004, "name": "Włącznik OKAP"},
    "contamination_sensor":   {"address": 0x0005, "name": "Czujnik jakości powietrza"},
    "airing_sensor":          {"address": 0x0006, "name": "Czujnik wilgotności"},
    "airing_switch":          {"address": 0x0007, "name": "Włącznik WIETRZENIE"},
    "airing_mini":            {"address": 0x000A, "name": "Przełącznik AirS - Wietrzenie"},
    "fan_speed_3":            {"address": 0x000B, "name": "Przełącznik AirS - 3 bieg"},
    "fan_speed_2":            {"address": 0x000C, "name": "Przełącznik AirS - 2 bieg"},
    "fan_speed_1":            {"address": 0x000D, "name": "Przełącznik AirS - 1 bieg"},
    "fireplace":              {"address": 0x000E, "name": "Włącznik KOMINEK"},
    "ppoz":                   {"address": 0x000F, "name": "Alarm pożarowy P.POZ"},
    "dp_ahu_filter_overflow": {"address": 0x0012, "name": "Presostat filtrów rekuperatora (DP1)"},
    "ahu_filter_protection":  {"address": 0x0013, "name": "Zabezpieczenie termiczne nagrzewnicy FPX"},
    "empty_house":            {"address": 0x0015, "name": "Pusty dom"},
}

# ─── 04 READ INPUT REGISTERS ─────────────────────────────────────────────────
INPUT_REGISTERS = {
    # Temperatures (multiplier ×0.1, 0x8000 = no reading)
    "outside_temperature":      {"address": 0x0010, "name": "Temperatura zewnętrzna (TZ1)",        "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "supply_temperature":       {"address": 0x0011, "name": "Temperatura nawiewu (TN1)",            "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "exhaust_temperature":      {"address": 0x0012, "name": "Temperatura wywiewu (TP)",             "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "fpx_temperature":          {"address": 0x0013, "name": "Temperatura za nagrzewnicą FPX (TZ2)","unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "duct_supply_temperature":  {"address": 0x0014, "name": "Temperatura za nagrzewnicą/chłodnicą kanałową (TN2)", "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "gwc_temperature":          {"address": 0x0015, "name": "Temperatura GWC (TZ3)",               "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    "ambient_temperature":      {"address": 0x0016, "name": "Temperatura otoczenia (TO)",           "unit": "°C", "scale": 0.1, "device_class": "temperature"},
    # Airflow
    "supply_percentage":        {"address": 0x0110, "name": "Intensywność nawiewu",                "unit": "%",  "scale": 1,   "device_class": None},
    "exhaust_percentage":       {"address": 0x0111, "name": "Intensywność wywiewu",                "unit": "%",  "scale": 1,   "device_class": None},
    "supply_flowrate":          {"address": 0x0112, "name": "Strumień nawiewu",                    "unit": "m³/h","scale": 1,  "device_class": None},
    "exhaust_flowrate":         {"address": 0x0113, "name": "Strumień wywiewu",                    "unit": "m³/h","scale": 1,  "device_class": None},
    "min_percentage":           {"address": 0x0114, "name": "Min. intensywność wentylacji",        "unit": "%",  "scale": 1,   "device_class": None},
    "max_percentage":           {"address": 0x0115, "name": "Max. intensywność wentylacji",        "unit": "%",  "scale": 1,   "device_class": None},
    "water_removal_active":     {"address": 0x012A, "name": "Procedura HEWR aktywna",              "unit": None, "scale": 1,   "device_class": None},
    "constant_flow_active":     {"address": 0x010F, "name": "System Constant Flow aktywny",        "unit": None, "scale": 1,   "device_class": None},
    # Airflow (from CF module)
    "supply_air_flow_cf":       {"address": 0x0100, "name": "Strumień nawiewu CF",                 "unit": "m³/h","scale": 1,  "device_class": None},
    "exhaust_air_flow_cf":      {"address": 0x0101, "name": "Strumień wywiewu CF",                 "unit": "m³/h","scale": 1,  "device_class": None},
}

# ─── 03 READ/WRITE HOLDING REGISTERS ────────────────────────────────────────
HOLDING_REGISTERS = {
    # Operating mode
    "mode":                         {"address": 0x1070, "name": "Tryb pracy",                         "min": 0, "max": 2},
    "season_mode":                  {"address": 0x1071, "name": "Harmonogram (Lato/Zima)",             "min": 0, "max": 1},
    "air_flow_manual":              {"address": 0x1072, "name": "Intensywność wentylacji (manual)",    "min": 10,"max": 100, "unit": "%"},
    "air_flow_temporary":           {"address": 0x1073, "name": "Intensywność wentylacji (chwilowy)", "min": 10,"max": 100, "unit": "%"},
    "supply_temp_manual":           {"address": 0x1074, "name": "Temperatura nawiewu (manual)",       "min": 20,"max": 90,  "unit": "°C", "scale": 0.5},
    "supply_temp_temporary":        {"address": 0x1075, "name": "Temperatura nawiewu (chwilowy)",     "min": 20,"max": 90,  "unit": "°C", "scale": 0.5},
    # Fan speeds for AirS panel
    "fan_speed_1_coef":             {"address": 0x1078, "name": "Nastawa 1 bieg AirS",                "min": 10,"max": 45,  "unit": "%"},
    "fan_speed_2_coef":             {"address": 0x1079, "name": "Nastawa 2 bieg AirS",                "min": 46,"max": 75,  "unit": "%"},
    "fan_speed_3_coef":             {"address": 0x107A, "name": "Nastawa 3 bieg AirS",                "min": 76,"max": 100, "unit": "%"},
    # Special modes/functions
    "special_mode":                 {"address": 0x1080, "name": "Funkcja specjalna",                  "min": 0, "max": 11},
    "comfort_mode_panel":           {"address": 0x10D0, "name": "Tryb EKO/KOMFORT",                   "min": 0, "max": 1},
    # Hood
    "hood_supply_coef":             {"address": 0x1082, "name": "Intensywność OKAP (nawiew)",         "min": 100,"max": 150,"unit": "%"},
    "hood_exhaust_coef":            {"address": 0x1083, "name": "Intensywność OKAP (wywiew)",         "min": 100,"max": 150,"unit": "%"},
    # Fireplace
    "fireplace_supply_coef":        {"address": 0x1084, "name": "Różnicowanie strumieni KOMINEK",     "min": 5, "max": 50,  "unit": "%"},
    "fireplace_mode_time":          {"address": 0x108D, "name": "Czas działania KOMINEK",             "min": 1, "max": 10,  "unit": "min"},
    # Airing
    "airing_bathroom_coef":         {"address": 0x1085, "name": "Intensywność WIETRZENIE (łazienka)","min": 100,"max": 150,"unit": "%"},
    "airing_coef":                  {"address": 0x1086, "name": "Intensywność WIETRZENIE (pokoje)",  "min": 100,"max": 150,"unit": "%"},
    "contamination_coef":           {"address": 0x1087, "name": "Intensywność WIETRZENIE (JP)",      "min": 100,"max": 150,"unit": "%"},
    "airing_panel_mode_time":       {"address": 0x1089, "name": "Czas WIETRZENIE (ręczne)",          "min": 1, "max": 45,  "unit": "min"},
    "airing_switch_mode_time":      {"address": 0x108A, "name": "Czas WIETRZENIE (przełącznik)",     "min": 1, "max": 45,  "unit": "min"},
    "airing_switch_on_delay":       {"address": 0x108B, "name": "Opóźnienie załączenia WIETRZENIE",  "min": 0, "max": 20,  "unit": "min"},
    "airing_switch_off_delay":      {"address": 0x108C, "name": "Opóźnienie wyłączenia WIETRZENIE",  "min": 0, "max": 20,  "unit": "min"},
    # Empty house
    "empty_house_coef":             {"address": 0x1088, "name": "Intensywność PUSTY DOM",            "min": 10,"max": 50,  "unit": "%"},
    # Bypass
    "bypass_off":                   {"address": 0x10E0, "name": "Dezaktywacja bypass",               "min": 0, "max": 1},
    "bypass_mode":                  {"address": 0x10EA, "name": "Status bypass",                     "min": 0, "max": 2},
    "bypass_user_mode":             {"address": 0x10EB, "name": "Tryb bypass",                       "min": 1, "max": 3},
    "min_bypass_temperature":       {"address": 0x10E1, "name": "Min. temp. zewn. bypass",           "min": 10,"max": 40,  "unit": "°C", "scale": 0.5},
    "bypass_temp_freeheating":      {"address": 0x10E2, "name": "Temp. aktywacji bypass (grzanie)",  "min": 30,"max": 60,  "unit": "°C", "scale": 0.5},
    "bypass_temp_freecooling":      {"address": 0x10E3, "name": "Temp. aktywacji bypass (chłodzenie)","min": 30,"max": 60, "unit": "°C", "scale": 0.5},
    "bypass_coef1":                 {"address": 0x10EC, "name": "Różnicowanie strumieni bypass (tryb 2)","min": 10,"max": 100,"unit": "%"},
    "bypass_coef2":                 {"address": 0x10ED, "name": "Intensywność nawiewu bypass (tryb 2/3)","min": 10,"max": 151,"unit": "%"},
    # GWC
    "gwc_off":                      {"address": 0x10A0, "name": "Dezaktywacja GWC",                  "min": 0, "max": 1},
    "gwc_mode":                     {"address": 0x10A7, "name": "Status GWC",                        "min": 0, "max": 2},
    "min_gwc_temperature":          {"address": 0x10A1, "name": "Dolny próg temperatury GWC",        "min": 0, "max": 20,  "unit": "°C", "scale": 0.5},
    "max_gwc_temperature":          {"address": 0x10A2, "name": "Górny próg temperatury GWC",        "min": 30,"max": 80,  "unit": "°C", "scale": 0.5},
    "gwc_regen":                    {"address": 0x10A6, "name": "Typ regeneracji GWC",               "min": 0, "max": 2},
    "gwc_regen_period":             {"address": 0x10A8, "name": "Czas regeneracji GWC",              "min": 4, "max": 8,   "unit": "h"},
    # ON/OFF
    "on_off":                       {"address": 0x1123, "name": "Włączenie/wyłączenie urządzenia",   "min": 0, "max": 1},
    # Antifreeze
    "antifreeze_mode":              {"address": 0x1060, "name": "System FPX aktywny",                "min": 0, "max": 1},
    "antifreeze_stage":             {"address": 0x1066, "name": "Tryb FPX",                          "min": 0, "max": 2},
    # Comfort
    "comfort_mode_status":          {"address": 0x10D1, "name": "Status trybu KOMFORT",              "min": 0, "max": 2},
    "required_temp":                {"address": 0x1FFE, "name": "Temperatura zadana (KOMFORT)",      "min": 20,"max": 90,  "unit": "°C", "scale": 0.5},
    # Alarm stop code
    "stop_ahu_code":                {"address": 0x1120, "name": "Kod alarmu blokującego (typ S)",    "min": 0, "max": 98},
    # Filter
    "filter_change":                {"address": 0x1FFF, "name": "Typ filtra",                        "min": 1, "max": 4},
    # DAC
    "dac_supply":                   {"address": 0x0500, "name": "Napięcie sterujące nawiewem (PWM)", "unit": "V", "scale": 0.00244},
    "dac_exhaust":                  {"address": 0x0501, "name": "Napięcie sterujące wywiewem (PWM)","unit": "V", "scale": 0.00244},
    "dac_heater":                   {"address": 0x0502, "name": "Napięcie sterujące nagrzewnicą (PWM)","unit": "V","scale": 0.00244},
    "dac_cooler":                   {"address": 0x0503, "name": "Napięcie sterujące chłodnicą (PWM)","unit": "V", "scale": 0.00244},
}

# ─── ALARM REGISTERS (03 holding, read/write) ────────────────────────────────
ALARM_REGISTERS = {
    # S-type (blocking)
    "S2":  {"address": 0x2002, "name": "Błąd komunikacji I2C"},
    "S6":  {"address": 0x2006, "name": "Zabezpieczenie termiczne FPX (max razy)"},
    "S7":  {"address": 0x2007, "name": "Kalibracja niemożliwa (niska temp. zewn.)"},
    "S8":  {"address": 0x2008, "name": "Wymagany klucz produktu"},
    "S9":  {"address": 0x2009, "name": "Zatrzymano z panelu AirS"},
    "S10": {"address": 0x200A, "name": "Zadziałał czujnik PPOŻ"},
    "S13": {"address": 0x200D, "name": "Zatrzymano z panelu sterowania/aplikacji"},
    "S14": {"address": 0x200E, "name": "Zabezpieczenie przeciwzamrożeniowe (max razy)"},
    "S15": {"address": 0x200F, "name": "Brak rezultatu zabezpieczenia przeciwzamrożeniowego"},
    "S16": {"address": 0x2010, "name": "Zabezpieczenie termiczne nagrzewnicy elektrycznej"},
    "S17": {"address": 0x2011, "name": "Filtry nie wymienione (presostat)"},
    "S19": {"address": 0x2013, "name": "Filtry nie wymienione (czas)"},
    "S20": {"address": 0x2014, "name": "Filtr kanałowy nie wymieniony"},
    "S22": {"address": 0x2016, "name": "Błąd zabezpieczenia przeciwzamrożeniowe FPX"},
    "S23": {"address": 0x2017, "name": "Uszkodzony czujnik TZ2 (FPX)"},
    "S24": {"address": 0x2018, "name": "Uszkodzony czujnik TN2"},
    "S25": {"address": 0x2019, "name": "Uszkodzony czujnik temp. zewnętrznej"},
    "S26": {"address": 0x201A, "name": "Uszkodzone czujniki TZ1 i TZ3"},
    "S29": {"address": 0x201D, "name": "Zbyt wysoka temperatura przed rekuperatorem"},
    "S30": {"address": 0x201E, "name": "Awaria wentylatora nawiewnego"},
    "S31": {"address": 0x201F, "name": "Awaria wentylatora wywiewnego"},
    "S32": {"address": 0x2020, "name": "Brak komunikacji z modułem TG-02"},
    # E-type (warnings)
    "E99": {"address": 0x2063, "name": "Wymagany klucz produktu"},
    "E100":{"address": 0x2064, "name": "Brak odczytu czujnika TZ1"},
    "E101":{"address": 0x2065, "name": "Brak odczytu czujnika TN1"},
    "E102":{"address": 0x2066, "name": "Brak odczytu czujnika TP"},
    "E103":{"address": 0x2067, "name": "Brak odczytu czujnika TZ2"},
    "E104":{"address": 0x2068, "name": "Brak odczytu czujnika TO"},
    "E105":{"address": 0x2069, "name": "Brak odczytu czujnika TN2"},
    "E106":{"address": 0x206A, "name": "Brak odczytu czujnika TZ3"},
    "E138":{"address": 0x208A, "name": "Awaria czujnika CF (nawiew)"},
    "E139":{"address": 0x208B, "name": "Awaria czujnika CF (wywiew)"},
    "E152":{"address": 0x2098, "name": "Temperatura wywiewu za wysoka"},
    "E196":{"address": 0x20C6, "name": "Regulacja instalacji nie wykonana"},
    "E197":{"address": 0x20C7, "name": "Regulacja instalacji przerwana"},
    "E200":{"address": 0x20C8, "name": "Zabezpieczenie termiczne nagrzewnicy elektrycznej (ostrzeżenie)"},
    "E201":{"address": 0x20C9, "name": "Zabezpieczenie termiczne nagrzewnicy kanałowej"},

    "E249":{"address": 0x20F9, "name": "Brak komunikacji z modułem Expansion"},
    "E250":{"address": 0x20FA, "name": "Konieczność wymiany filtrów (czas)"},
    "E251":{"address": 0x20FB, "name": "Konieczność wymiany filtra kanałowego"},
    "E252":{"address": 0x20FC, "name": "Konieczność wymiany filtrów (presostat)"},
}

# ─── Temporary Mode Registers ───────────────────────────────────────────────
# These registers are used to activate temporary mode (Wietrzenie / Airing)
# as described in PDF page 14.
CFG_MODE_1_ADDR = 0x1130        # Mode (0=auto, 1=manual, 2=temporary)
AIR_FLOW_TEMP_ADDR = 0x1131      # Intensity setpoint for temporary mode
AIR_FLOW_TEMP_FLAG_ADDR = 0x1132 # Activation flag (set to 1 to apply)

CFG_MODE_2_ADDR = 0x1133        # Mode for temperature temporary change
SUPPLY_TEMP_TEMP_ADDR = 0x1134   # Temperature setpoint for temporary mode
SUPPLY_TEMP_TEMP_FLAG_ADDR = 0x1135 # Activation flag (set to 1 to apply)


# ─── Mode mappings ────────────────────────────────────────────────────────────
MODE_MAP = {0: "Automatyczny", 1: "Manualny", 2: "Chwilowy"}
SEASON_MAP = {0: "Lato", 1: "Zima"}
BYPASS_MODE_MAP = {0: "Nieaktywny", 1: "Grzanie (freeheating)", 2: "Chłodzenie (freecooling)"}
BYPASS_USER_MODE_MAP = {1: "Tryb 1", 2: "Tryb 2", 3: "Tryb 3"}
GWC_MODE_MAP = {0: "Nieaktywny", 1: "Tryb zima", 2: "Tryb lato"}
GWC_REGEN_MAP = {0: "Brak", 1: "Dobowa", 2: "Temperaturowa"}
COMFORT_MODE_MAP = {0: "EKO", 1: "KOMFORT"}
COMFORT_STATUS_MAP = {0: "Nieaktywny", 1: "Grzanie", 2: "Chłodzenie"}
SPECIAL_MODE_MAP = {
    0: "Brak",
    1: "OKAP",
    2: "KOMINEK",
    3: "WIETRZENIE (przełącznik dzwonkowy)",
    4: "WIETRZENIE (ON/OFF)",
    5: "H2O/WIETRZENIE (higrostat)",
    6: "JP/WIETRZENIE (czujnik jakości powietrza)",
    7: "WIETRZENIE (ręczne)",
    8: "WIETRZENIE (harmonogram AUTO)",
    9: "WIETRZENIE (harmonogram MANUAL)",
    10: "OTWARTE OKNA",
    11: "PUSTY DOM",
}
FILTER_TYPE_MAP = {1: "Presostat", 2: "Filtry płaskie", 3: "Filtry CleanPad", 4: "Filtry CleanPad Pure"}
ANTIFREEZE_STAGE_MAP = {0: "OFF", 1: "FPX1", 2: "FPX2"}
LANGUAGE_MAP = {0: "PL", 1: "EN", 2: "RU", 3: "UK", 4: "SK"}
