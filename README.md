# AirPack Home – Home Assistant Integration

Integracja dla rekuperatorów **Theslagreen AirPack Home** (wszystkie modele h/v/f Energy/Energy+) przez protokół **Modbus RTU** (RS485 → USB).

## Główne cechy
- **Automatyczne wykrywanie USB:** Integracja sama wykrywa podłączony adapter RS485.
- **Stabilne połączenie:** Automatycznie używa ścieżek `/dev/serial/by-id/`, dzięki czemu nie stracisz połączenia po restarcie serwera.
- **Pełna kontrola:** Obsługa wentylatora (Fan), trybów pracy (Auto/Manual/Boost), bypassu i harmonogramów.
- **Diagnostyka:** Odczyt wszystkich temperatur, przepływów (CF), napięć PWM i pełna lista alarmów.

## Wymagania

- Home Assistant 2024.1.0+
- Adapter RS485 → USB (np. CH340, FTDI, CP210x) podłączony do serwera HA
- Połączenie z rekuperatorem kablem RS485

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

## Encje

### 🌬️ Wentylator (Fan)
Główna encja `fan.airpack_home` pozwala na:
- Włączanie/wyłączanie rekuperatora.
- Ustawianie intensywności (0-100%).
- Wybór trybów: **Automatyczny**, **Manualny**, **Boost (Wietrzenie)**.

### 🌡️ Sensory temperatury
| Encja | Opis |
|-------|------|
| `sensor.airpack_home_temperatura_zewnetrzna_tz1` | Temperatura zewnętrzna (TZ1) |
| `sensor.airpack_home_temperatura_nawiewu_tn1` | Temperatura powietrza nawiewanego |
| `sensor.airpack_home_temperatura_wywiewu_tp` | Temperatura powietrza wywiewanego |
| `sensor.airpack_home_sprawnosc_odzysku_ciepla` | Obliczana sprawność rekuperacji (%) |
| `sensor.airpack_home_temperatura_fpx_tz2` | Temperatura za nagrzewnicą FPX |
| `sensor.airpack_home_temperatura_otoczenia_to` | Temperatura otoczenia |

### 💨 Sensory przepływu i diagnostyka
| Encja | Opis |
|-------|------|
| `sensor.airpack_home_strumien_nawiewu_cf` | Chwilowy strumień nawiewu (CF) |
| `sensor.airpack_home_strumien_wywiewu_cf` | Chwilowy strumień wywiewu (CF) |
| `sensor.airpack_home_napiecie_nawiewu_pwm` | Napięcie sterujące wentylatorem nawiewnym (V) |
| `sensor.airpack_home_napiecie_wywiewu_pwm` | Napięcie sterujące wentylatorem wywiewnym (V) |
| `binary_sensor.airpack_home_system_fpx_aktywny` | Status systemu przeciwzamrożeniowego |

### ⚙️ Sterowanie (Select / Switch / Number)
- **Tryby:** Lato/Zima, EKO/KOMFORT.
- **Bypass:** Ręczne wymuszanie lub automatyka.
- **Nastawy:** Czas wietrzenia, progi temperatur, konfiguracja biegów AirS.
- **Czas:** Integracja automatycznie synchronizuje zegar rekuperatora z czasem HA codziennie o 03:00.

### 🚨 Alarmy (binary_sensor)
Wszystkie alarmy typu S (blokujące) i E (ostrzeżenia) są monitorowane i widoczne jako osobne sensory binarne z klasą `problem`.

## Licencja

MIT
