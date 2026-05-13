# AirPack Home – Home Assistant Integration

🇵🇱*(Polska wersja dokumentacji znajduje się poniżej)*🇵🇱

Integration for **Theslagreen AirPack Home** heat recovery units (all h/v/f Energy/Energy+ models) via **Modbus RTU** (RS485 → USB).

## Key Features
- **Automatic USB Discovery:** The integration automatically detects your connected RS485 adapter.
- **Stable Connection:** Uses `/dev/serial/by-id/` paths automatically to ensure connectivity persists after reboots.
- **Full Control:** Supports Fan entity (speed 0-100%), operation modes (Auto/Manual/Boost), bypass control, and schedules.
- **Diagnostics:** Monitoring of all temperatures, airflow rates (CF), PWM voltages, and a full list of alarms.
- **Time Sync:** Automatically synchronizes the unit's clock with Home Assistant daily at 03:00.

## Requirements
- Home Assistant 2024.1.0+
- RS485 → USB Adapter (e.g., CH340, FTDI, CP210x)


## Installation via HACS
1. Open HACS → Integrations → **⋮ → Custom repositories**
2. Add your repository URL, Category: `Integration`
3. Search for **AirPack Home** and click Install
4. Restart Home Assistant

## Configuration
1. Settings → Devices & Services → **Add Integration** → search for "AirPack Home"
2. If an adapter is connected, it may be discovered automatically. Otherwise, select the port from the dropdown list.
3. Provide:
   - **Port**: Select from the list (recommended) or enter manually.
   - **Modbus Slave ID**: default is `10` (check unit label)
   - **Baudrate**: default is `9600`

---

# AirPack Home – Integracja Home Assistant 🇵🇱

Integracja dla rekuperatorów **Theslagreen AirPack Home** (wszystkie modele h/v/f Energy/Energy+) przez protokół **Modbus RTU** (RS485 → USB).

## Główne cechy
- **Automatyczne wykrywanie USB:** Integracja sama wykrywa podłączony adapter RS485.
- **Stabilne połączenie:** Automatycznie używa ścieżek `/dev/serial/by-id/`, dzięki czemu nie stracisz połączenia po restarcie serwera.
- **Pełna kontrola:** Obsługa wentylatora (Fan), trybów pracy (Auto/Manual/Boost), bypassu i harmonogramów.
- **Diagnostyka:** Odczyt wszystkich temperatur, przepływów (CF), napięć PWM i pełna lista alarmów.
- **Synchronizacja czasu:** Automatycznie synchronizuje zegar rekuperatora z czasem HA codziennie o 03:00.

## Wymagania
- Home Assistant 2024.1.0+
- Adapter RS485 → USB (np. CH340, FTDI, CP210x) podłączony do serwera HA


## Instalacja przez HACS
1. Otwórz HACS → Integracje → **⋮ → Repozytoria niestandardowe**
2. Dodaj URL swojego repozytorium, typ: `Integration`
3. Wyszukaj **AirPack Home** i kliknij Zainstaluj
4. Uruchom ponownie Home Assistant

## Konfiguracja
1. Ustawienia → Urządzenia i usługi → **Dodaj integrację** → szukaj „AirPack Home"
2. Jeśli masz podłączony adapter, integracja może zostać wykryta automatycznie. Jeśli nie, wybierz port z listy rozwijanej.
3. Podaj:
   - **Port**: Wybierz z listy (zalecane) lub wpisz ręcznie.
   - **Adres Modbus**: domyślnie `10` (patrz etykieta urządzenia)
   - **Baudrate**: domyślnie `9600`

## Encje / Entities

### 🌬️ Fan / Wentylator
Main entity `fan.airpack_home` / Główna encja:
- On/Off, Speed 0-100%
- Preset modes: **Automatyczny (Auto)**, **Manualny (Manual)**, **Boost (Wietrzenie)**.

### 🌡️ Temperatures / Temperatury
- `outside_temperature` (TZ1)
- `supply_temperature` (TN1)
- `exhaust_temperature` (TP)
- `heat_recovery_efficiency` (%)
- `fpx_temperature` (TZ2)
- `ambient_temperature` (TO)

### 🚨 Alarms / Alarmy
All S-type (blocking) and E-type (warning) alarms are monitored as binary sensors with `problem` device class.
Wszystkie alarmy typu S i E są monitorowane jako sensory binarne.

## License / Licencja
MIT

---

## Credits

This integration was developed with the assistance of **MIX AI**.  
The AI generated the code based on the official Modbus RTU register documentation  
provided by Theslagreen. Testing, validation and real-world verification  
was performed by the repository author.

---

## Podziękowania 🇵🇱

Integracja została napisana przy pomocy **MIX AI**.  
Kod powstał na podstawie oficjalnej dokumentacji rejestrów Modbus RTU  
dostarczonej przez Theslagreen. Testowanie i weryfikacja na rzeczywistym  
urządzeniu zostały wykonane przez autora repozytorium.
