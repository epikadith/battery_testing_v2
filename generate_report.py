import parsing
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

def plot_battery_level_for_pdf(battery_df):
    """Generates the battery level plot and returns it as a ReportLab Image."""
    if battery_df.empty:
        return None
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(10, 5))
    battery_df.plot(y='level', marker='o', ax=ax)
    ax.set_title('Battery Level Over Time')
    ax.set_ylabel('Battery Level (%)')
    ax.set_ylim(0, 100)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=7*inch, height=3.5*inch)

def plot_top_consumers_for_pdf(power_df, top_n=15):
    """Generates the top consumers plot and returns it as a ReportLab Image."""
    if power_df.empty:
        return None
    top_consumers = power_df.head(top_n)
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.barplot(x='power_mah', y='name', data=top_consumers, ax=ax, palette='viridis')
    ax.set_title(f'Top {top_n} Power Consumers (Total mAh)')
    ax.set_xlabel('Total Power Consumed (mAh)')
    ax.set_ylabel('Application / Component')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=7*inch, height=5*inch)

def plot_top_longwakes_for_pdf(wakelock_df, top_n=20):
    """Generates the top longwakes plot and returns it as a ReportLab Image."""
    if wakelock_df.empty:
        return None
    top_items = wakelock_df.head(top_n).copy()
    if 'app_name' in top_items.columns:
        top_items['label'] = top_items['app_name'] + ': ' + top_items['tag'].str.split('/').str[-1]
    else:
        top_items['label'] = top_items['uid'] + ': ' + top_items['tag']
    
    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.barplot(x='duration_s', y='label', data=top_items, ax=ax, palette='plasma')
    ax.set_title(f'Top {top_n} Longwake Durations')
    ax.set_xlabel('Total Duration (seconds)')
    ax.set_ylabel('Wakelock App & Tag')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return Image(buffer, width=7*inch, height=6*inch)

def df_to_table(df, font_size=8):
    """Converts a pandas DataFrame to a ReportLab Table object with styling."""
    # Round numeric columns to 3 decimal places for cleaner display
    df_rounded = df.round(3)
    data = [df_rounded.columns.to_list()] + df_rounded.values.tolist()
    
    table = Table(data, hAlign='LEFT')
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    return table

def create_report():
    """Generates a complete PDF report of the battery analysis."""
    print("Starting report generation...")
    
    # 1. Setup paths and get data
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    pdf_path = results_dir / f"battery_report_{timestamp}.pdf"

    print("Processing logs...")
    battery_df, power_df, longwake_df = parsing.process_all_logs()
    
    # Re-create combined_df logic from the notebook
    if not longwake_df.empty:
        # This logic is from the notebook to get app names from wakelock tags
        def get_package_name_from_tag(tag):
            import re
            match = re.search(r'([a-zA-Z0-9_]+\.[a-zA-Z0-9_\.]+)', tag)
            return match.group(1) if match else 'System/Other'
        
        longwake_df['name'] = longwake_df['tag'].apply(get_package_name_from_tag)
        app_wakelocks = longwake_df.groupby('name')['duration_s'].sum().reset_index()
        
        if not power_df.empty:
            combined_df = pd.merge(power_df, app_wakelocks, on='name', how='outer').fillna(0)
            combined_df['drain_score'] = (combined_df['power_mah'] * 0.7) + (combined_df['duration_s'] * 0.3)
            combined_df = combined_df.sort_values(by='drain_score', ascending=False)
        else:
            combined_df = pd.DataFrame()
    else:
        combined_df = pd.DataFrame()

    # 2. Build PDF story
    doc = SimpleDocTemplate(str(pdf_path))
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Battery Drain Analysis Report", styles['h1']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # --- Device Info ---
    print("Adding device info...")
    story.append(Paragraph("1. Device Information", styles['h2']))
    log_dirs = parsing.get_log_dirs()
    if log_dirs:
        latest_log_dir = log_dirs[-1]
        device_info = parsing.parse_device_info(latest_log_dir)
        info_data = [
            ['Log Source:', latest_log_dir.name],
            ['Phone Model:', device_info.get('model', 'N/A')],
            ['Android OS Version:', device_info.get('android_version', 'N/A')],
            ['Estimated Battery Health:', device_info.get('battery_health_percent', 'N/A')]
        ]
        story.append(df_to_table(pd.DataFrame(info_data, columns=['Metric', 'Value'])))
    else:
        story.append(Paragraph("Could not find log directories.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # --- Battery Level ---
    print("Adding battery level plot...")
    story.append(Paragraph("2. Battery Level Over Time", styles['h2']))
    battery_plot = plot_battery_level_for_pdf(battery_df)
    if battery_plot:
        story.append(battery_plot)
    else:
        story.append(Paragraph("No battery level data found.", styles['Normal']))
    story.append(PageBreak())

    # --- Power Consumers ---
    print("Adding power consumption analysis...")
    story.append(Paragraph("3. Top Power Consumers", styles['h2']))
    story.append(Paragraph("This section identifies which apps and components used the most power (in mAh).", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    if not power_df.empty:
        story.append(df_to_table(power_df.head(15)))
        story.append(Spacer(1, 0.2 * inch))
        power_plot = plot_top_consumers_for_pdf(power_df)
        if power_plot:
            story.append(power_plot)
    else:
        story.append(Paragraph("No power consumption data found.", styles['Normal']))
    story.append(PageBreak())

    # --- Wakelock Analysis ---
    print("Adding wakelock analysis...")
    story.append(Paragraph("4. Wakelock Analysis", styles['h2']))
    story.append(Paragraph("This section shows which processes held wakelocks the longest, preventing the device from sleeping.", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    if not longwake_df.empty:
        story.append(df_to_table(longwake_df.head(15)))
        story.append(Spacer(1, 0.2 * inch))
        longwake_plot = plot_top_longwakes_for_pdf(longwake_df)
        if longwake_plot:
            story.append(longwake_plot)
    else:
        story.append(Paragraph("No longwake data found.", styles['Normal']))
    story.append(PageBreak())
    
    # --- Combined Analysis ---
    print("Adding combined analysis...")
    story.append(Paragraph("5. Combined Drain Score Analysis", styles['h2']))
    story.append(Paragraph("This table merges power and wakelock data to find the top overall battery offenders.", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    if not combined_df.empty:
        story.append(df_to_table(combined_df.head(20)))
    else:
        story.append(Paragraph("Could not generate combined analysis.", styles['Normal']))

    # 3. Build the PDF
    print("Building PDF...")
    doc.build(story)
    print(f"\nSuccessfully generated report: {pdf_path}")

if __name__ == '__main__':
    create_report()
