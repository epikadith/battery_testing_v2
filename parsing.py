import re
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# --- CONFIGURATION ---
LOGS_DIR = Path(__file__).parent / 'logs'

# --- PARSING FUNCTIONS ---

def get_log_dirs():
    """Finds and sorts all timestamped log directories."""
    if not LOGS_DIR.is_dir():
        return []
    log_dirs = [d for d in LOGS_DIR.iterdir() if d.is_dir()]
    log_dirs.sort(key=lambda x: datetime.strptime(x.name, '%Y-%m-%d_%H-%M'))
    return log_dirs

def parse_battery_level(file_path):
    try:
        content = file_path.read_text()
        match = re.search(r'level:\s*(\d+)', content)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Could not parse {file_path}: {e}")
    return None

def parse_power_consumers(file_path):
    consumers = []
    try:
        content = file_path.read_text()
        in_power_section = False
        consumer_regex = re.compile(r'^\s{2,}(.+?):\s*([\d\.]+)')
        for line in content.splitlines():
            if 'Estimated power use (mAh)' in line:
                in_power_section = True
                continue
            if in_power_section:
                if not line.strip() or 'Per-app mobile ms per packet' in line:
                    break
                if 'Capacity:' in line or 'Computed drain:' in line:
                    continue
                match = consumer_regex.search(line)
                if match:
                    full_name, power_mah = match.groups()
                    name = re.sub(r'Uid [^\s]+ \((.*)\)', r'\1', full_name).strip()
                    consumers.append({'name': name, 'power_mah': float(power_mah)})
    except Exception as e:
        print(f"Could not parse power consumers from {file_path}: {e}")
    return consumers

def parse_time(time_str):
    h, m, s, ms = 0, 0, 0, 0
    time_str = time_str.strip()
    if 'h' in time_str:
        h_match = re.search(r'(\d+)h', time_str)
        if h_match: h = int(h_match.group(1))
    if 'm' in time_str:
        m_match = re.search(r'(\d+)m', time_str)
        if m_match: m = int(m_match.group(1))
    if 's' in time_str:
        s_match = re.search(r'(\d+)s', time_str)
        if s_match: s = int(s_match.group(1))
    if 'ms' in time_str:
        ms_match = re.search(r'(\d+)ms', time_str)
        if ms_match: ms = int(ms_match.group(1))
    return timedelta(hours=h, minutes=m, seconds=s, milliseconds=ms)

def parse_battery_history(file_path):
    """More robust parser for the 'Battery History' section."""
    events = []
    start_time = None
    try:
        content = file_path.read_text()
        reset_time_match = re.search(r'RESET:TIME: (\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})', content)
        if not reset_time_match:
            return pd.DataFrame()
        start_time = datetime.strptime(reset_time_match.group(1), '%Y-%m-%d-%H-%M-%S')

        # Regex for the event part, not the whole line
        longwake_regex = re.compile(r'([+-])longwake=([^:]+):"(.*?)"')
        
        # Anchor to find the start of the event details
        header_anchor_regex = re.compile(r'\(\d+\)\s+\d{3}\s+')

        for line in content.splitlines():
            anchor_match = header_anchor_regex.search(line)
            if not anchor_match:
                continue

            # The event details are everything after the anchor
            event_details = line[anchor_match.end():]
            # The timestamp is everything before the anchor
            timestamp_str = line[:anchor_match.start()].strip()

            if not timestamp_str.startswith('+'):
                continue

            current_time = start_time + parse_time(timestamp_str)

            for match in longwake_regex.finditer(event_details):
                status, uid, tag = match.groups()
                events.append({
                    'timestamp': current_time,
                    'type': 'longwake',
                    'status': 'start' if status == '+' else 'end',
                    'uid': uid,
                    'tag': tag
                })
    except Exception as e:
        print(f"Error parsing battery history from {file_path}: {e}")
    return pd.DataFrame(events)

# --- DATA PROCESSING & AGGREGATION ---

def process_all_logs():
    log_dirs = get_log_dirs()
    if not log_dirs:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    battery_df = pd.DataFrame([{'timestamp': datetime.strptime(d.name, '%Y-%m-%d_%H-%M'), 'level': parse_battery_level(d / 'battery.txt')} for d in log_dirs if parse_battery_level(d / 'battery.txt') is not None]).set_index('timestamp')

    power_data = []
    for log_dir in log_dirs:
        power_data.extend(parse_power_consumers(log_dir / 'batterystats.txt'))
    power_df = pd.DataFrame(power_data)
    total_power_df = power_df.groupby('name')['power_mah'].sum().sort_values(ascending=False).reset_index() if not power_df.empty else pd.DataFrame(columns=['name', 'power_mah'])

    all_events_df = pd.concat([parse_battery_history(log_dir / 'batterystats.txt') for log_dir in log_dirs])
    if all_events_df.empty:
        return battery_df, total_power_df, pd.DataFrame()

    all_events_df.sort_values('timestamp', inplace=True)
    starts = all_events_df[all_events_df['status'] == 'start'].copy()
    ends = all_events_df[all_events_df['status'] == 'end'].copy()
    
    wakelock_periods = []
    used_end_indices = set()

    for start_idx, start_event in starts.iterrows():
        potential_ends = ends[
            (ends['uid'] == start_event['uid']) &
            (ends['tag'] == start_event['tag']) &
            (ends['timestamp'] > start_event['timestamp']) &
            (~ends.index.isin(used_end_indices))
        ]
        
        if not potential_ends.empty:
            end_event = potential_ends.iloc[0]
            duration = (end_event['timestamp'] - start_event['timestamp']).total_seconds()
            
            if duration >= 0:
                wakelock_periods.append({
                    'uid': start_event['uid'],
                    'tag': start_event['tag'],
                    'duration_s': duration
                })
                used_end_indices.add(end_event.name)

    if not wakelock_periods:
        return battery_df, total_power_df, pd.DataFrame()

    longwake_summary_df = pd.DataFrame(wakelock_periods)
    total_longwake_df = longwake_summary_df.groupby(['uid', 'tag'])['duration_s'].sum().sort_values(ascending=False).reset_index()

    return battery_df, total_power_df, total_longwake_df

# --- VISUALIZATION FUNCTIONS ---

def plot_battery_level(battery_df):
    if battery_df.empty: return
    plt.style.use('ggplot')
    battery_df.plot(y='level', marker='o', figsize=(12, 6), title='Battery Level Over Time')
    plt.ylabel('Battery Level (%)')
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()

def plot_top_consumers(power_df, top_n=15):
    if power_df.empty: 
        print("No power consumption data found.")
        return
    top_consumers = power_df.head(top_n)
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.barplot(x='power_mah', y='name', data=top_consumers, ax=ax, palette='viridis')
    ax.set_title(f'Top {top_n} Power Consumers (Total mAh)')
    ax.set_xlabel('Total Power Consumed (mAh)')
    ax.set_ylabel('Application / Component')
    plt.tight_layout()
    plt.show()

def plot_top_longwakes(wakelock_df, top_n=20):
    if wakelock_df.empty:
        print("No significant longwake data to plot.")
        return
    top_items = wakelock_df.head(top_n).copy()
    top_items['label'] = top_items['uid'] + ': ' + top_items['tag']
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.barplot(x='duration_s', y='label', data=top_items, ax=ax, palette='plasma')
    ax.set_title(f'Top {top_n} Longwake Durations')
    ax.set_xlabel('Total Duration (seconds)')
    ax.set_ylabel('Wakelock UID & Tag')
    plt.tight_layout()
    plt.show()

# --- MAIN EXECUTION BLOCK ---

if __name__ == '__main__':
    print("Processing all battery logs...")
    battery_df, power_df, longwake_df = process_all_logs()

    if not battery_df.empty:
        print("\n--- Battery Level Analysis ---")
        plot_battery_level(battery_df)

    if not power_df.empty:
        print("\n--- Power Consumption Analysis ---")
        plot_top_consumers(power_df)
        
    if not longwake_df.empty:
        print("\n--- Longwake Analysis ---")
        plot_top_longwakes(longwake_df)
    else:
        print("\nNo longwake data was found.")

    print("\nAnalysis complete.")


def parse_device_info(log_dir_path):
    """(Corrected) Parses device info and battery health from a specific log directory."""
    info = {
        'model': 'N/A',
        'android_version': 'N/A',
        'battery_health_percent': 'N/A'
    }
    ORIGINAL_CAPACITY_MAH = 4500 # Original design capacity

    try:
        # (Corrected logic) Parse Model and OS Version from device_info.txt
        info_file = log_dir_path / 'device_info.txt'
        if info_file.exists():
            lines = info_file.read_text().splitlines()
            for i, line in enumerate(lines):
                if "Model:" in line and i + 1 < len(lines) and lines[i+1].strip():
                    info['model'] = lines[i+1].strip()
                if "Android Version:" in line and i + 1 < len(lines) and lines[i+1].strip():
                    info['android_version'] = lines[i+1].strip()

        # Parse battery capacity from batterystats.txt to calculate health
        stats_file = log_dir_path / 'batterystats.txt'
        if stats_file.exists():
            content = stats_file.read_text()
            cap_match = re.search(r'Capacity: (\d+)', content)
            if cap_match:
                current_capacity = int(cap_match.group(1))
                health = (current_capacity / ORIGINAL_CAPACITY_MAH) * 100
                info['battery_health_percent'] = f'{health:.1f}%'
    except Exception as e:
        print(f"Could not parse device info from {log_dir_path}: {e}")
        
    return info

def display_device_info():
    """Finds the latest log, parses device info, and prints it."""
    log_dirs = get_log_dirs()
    if not log_dirs:
        print("No log directories found.")
        return

    latest_log_dir = log_dirs[-1]
    info = parse_device_info(latest_log_dir)

    print("--- Device Information (from latest log) ---")
    print(f"  Log Source: {latest_log_dir.name}")
    print(f"  Phone Model: {info.get('model', 'N/A')}")
    print(f"  Android OS Version: {info.get('android_version', 'N/A')}")
    print(f"  Estimated Battery Health: {info.get('battery_health_percent', 'N/A')}")