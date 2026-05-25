"""
Retail Sales Analysis & Customer Segmentation — MySQL Version
=============================================================
End-to-end data analysis project:
  MySQL (10 business questions) → EDA → RFM Customer Segmentation → Business Recommendations

HOW TO RUN:
    1. Place this file in the same folder as online_retail.csv
    2. Fill in your MySQL password on line 30
    3. Run:
           python retail_analysis_mysql.py
    4. Results print to terminal. Charts saved to output_charts/ folder.
       All 10 SQL queries are also saved to retail_queries.sql
       so you can open and run them in MySQL Workbench.
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')
import mysql.connector
from mysql.connector import Error

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE CONFIG — fill in your password here
# ─────────────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'NMathebula@21',   
    'database': 'retail_db'
}

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.05)
OUTPUT_DIR = 'output_charts'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Chart saved: {path}")

def run_query(conn, sql):
    """Run a SQL query and return a DataFrame."""
    return pd.read_sql(sql, conn)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CONNECT & LOAD DATA INTO MYSQL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("STEP 1: Connecting to MySQL and loading data")
print("="*65)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    print("  Connected to MySQL successfully.")
except Error as e:
    print(f"  ERROR connecting to MySQL: {e}")
    print("  Check your password in DB_CONFIG at the top of this script.")
    exit()

# Load CSV
df = pd.read_csv('online_retail.csv')
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['Revenue'] = df['Quantity'] * df['UnitPrice']

print(f"  Rows loaded: {len(df):,}")
print(f"  Date range:  {df['InvoiceDate'].min().date()} → {df['InvoiceDate'].max().date()}")

# Create table
cursor.execute("DROP TABLE IF EXISTS transactions;")
cursor.execute("""
    CREATE TABLE transactions (
        InvoiceNo    VARCHAR(20),
        StockCode    VARCHAR(20),
        Description  VARCHAR(255),
        Quantity     INT,
        InvoiceDate  DATETIME,
        UnitPrice    DECIMAL(10,2),
        CustomerID   VARCHAR(20),
        Country      VARCHAR(100),
        Revenue      DECIMAL(10,2)
    );
""")
conn.commit()
print("  Table created: transactions")

# Insert data in batches of 1000 (fast)
insert_sql = """
    INSERT INTO transactions
    (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country, Revenue)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
batch = []
total = 0
for _, row in df.iterrows():
    batch.append((
        str(row['InvoiceNo']),
        str(row['StockCode']),
        str(row['Description']),
        int(row['Quantity']),
        row['InvoiceDate'].strftime('%Y-%m-%d %H:%M:%S'),
        float(row['UnitPrice']),
        None if pd.isna(row['CustomerID']) else str(row['CustomerID']),
        str(row['Country']),
        float(row['Revenue'])
    ))
    if len(batch) == 1000:
        cursor.executemany(insert_sql, batch)
        conn.commit()
        total += len(batch)
        batch = []
        print(f"  Inserted {total:,} rows...", end='\r')

if batch:
    cursor.executemany(insert_sql, batch)
    conn.commit()
    total += len(batch)

print(f"  Inserted {total:,} rows into MySQL.           ")


# ─────────────────────────────────────────────────────────────────────────────
# 2. SQL ANALYSIS — 10 BUSINESS QUESTIONS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("STEP 2: SQL Analysis — 10 Business Questions")
print("="*65)

# We collect all queries so we can save them to a .sql file at the end
all_queries = {}

# ── Q1: Total Revenue ─────────────────────────────────────────────────────
all_queries['Q1_total_revenue'] = """
SELECT ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue
FROM transactions
WHERE Quantity > 0
"""
result = run_query(conn, all_queries['Q1_total_revenue'])
print(f"\nQ1. Total Revenue: £{result['total_revenue'][0]:,.2f}")

# ── Q2: Monthly Revenue Trend ─────────────────────────────────────────────
all_queries['Q2_monthly_revenue'] = """
SELECT
    DATE_FORMAT(InvoiceDate, '%Y-%m')     AS month,
    ROUND(SUM(Quantity * UnitPrice), 2)   AS revenue,
    COUNT(DISTINCT InvoiceNo)             AS orders,
    COUNT(DISTINCT CustomerID)            AS unique_customers
FROM transactions
WHERE Quantity > 0
GROUP BY month
ORDER BY month
"""
monthly = run_query(conn, all_queries['Q2_monthly_revenue'])
print("\nQ2. Monthly Revenue Trend:")
print(monthly.to_string(index=False))

# ── Q3: Top 10 Products by Revenue ───────────────────────────────────────
all_queries['Q3_top_products'] = """
SELECT
    Description,
    SUM(Quantity)                        AS units_sold,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY Description
ORDER BY revenue DESC
LIMIT 10
"""
top_products = run_query(conn, all_queries['Q3_top_products'])
print("\nQ3. Top 10 Products by Revenue:")
print(top_products.to_string(index=False))

# ── Q4: Revenue by Country ────────────────────────────────────────────────
all_queries['Q4_revenue_by_country'] = """
SELECT
    Country,
    COUNT(DISTINCT CustomerID)           AS customers,
    COUNT(DISTINCT InvoiceNo)            AS orders,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY Country
ORDER BY revenue DESC
LIMIT 8
"""
country_rev = run_query(conn, all_queries['Q4_revenue_by_country'])
print("\nQ4. Revenue by Country:")
print(country_rev.to_string(index=False))

# ── Q5: Average Order Value ───────────────────────────────────────────────
all_queries['Q5_avg_order_value'] = """
SELECT
    ROUND(AVG(order_value), 2) AS avg_order_value,
    ROUND(MIN(order_value), 2) AS min_order_value,
    ROUND(MAX(order_value), 2) AS max_order_value
FROM (
    SELECT InvoiceNo, SUM(Quantity * UnitPrice) AS order_value
    FROM transactions
    WHERE Quantity > 0
    GROUP BY InvoiceNo
) AS order_totals
"""
aov = run_query(conn, all_queries['Q5_avg_order_value'])
print("\nQ5. Order Value Stats:")
print(aov.to_string(index=False))

# ── Q6: Top 10 Customers with CASE WHEN Tier ─────────────────────────────
all_queries['Q6_top_customers'] = """
SELECT
    CustomerID,
    Country,
    COUNT(DISTINCT InvoiceNo)            AS total_orders,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS total_revenue,
    CASE
        WHEN SUM(Quantity * UnitPrice) >= 1000 THEN 'High Value'
        WHEN SUM(Quantity * UnitPrice) >= 300  THEN 'Mid Value'
        ELSE 'Low Value'
    END AS customer_tier
FROM transactions
WHERE Quantity > 0 AND CustomerID IS NOT NULL
GROUP BY CustomerID, Country
ORDER BY total_revenue DESC
LIMIT 10
"""
top_customers = run_query(conn, all_queries['Q6_top_customers'])
print("\nQ6. Top 10 Customers by Revenue:")
print(top_customers.to_string(index=False))

# ── Q7: Revenue by Day of Week ────────────────────────────────────────────
all_queries['Q7_day_of_week'] = """
SELECT
    DAYNAME(InvoiceDate)                 AS day_of_week,
    COUNT(DISTINCT InvoiceNo)            AS orders,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY DAYNAME(InvoiceDate), DAYOFWEEK(InvoiceDate)
ORDER BY DAYOFWEEK(InvoiceDate)
"""
dow = run_query(conn, all_queries['Q7_day_of_week'])
print("\nQ7. Orders by Day of Week:")
print(dow.to_string(index=False))

# ── Q8: Cancellation Rate ─────────────────────────────────────────────────
all_queries['Q8_cancellation_rate'] = """
SELECT
    COUNT(CASE WHEN Quantity < 0 THEN 1 END)  AS cancelled_rows,
    COUNT(CASE WHEN Quantity > 0 THEN 1 END)  AS normal_rows,
    ROUND(
        COUNT(CASE WHEN Quantity < 0 THEN 1 END) * 100.0 / COUNT(*), 2
    ) AS cancellation_rate_pct
FROM transactions
"""
cancel = run_query(conn, all_queries['Q8_cancellation_rate'])
print("\nQ8. Cancellation Analysis:")
print(cancel.to_string(index=False))

# ── Q9: Products with Most Repeat Buyers (subquery) ──────────────────────
all_queries['Q9_repeat_buyers'] = """
SELECT Description, COUNT(*) AS repeat_purchase_customers
FROM (
    SELECT CustomerID, Description, COUNT(*) AS purchase_count
    FROM transactions
    WHERE Quantity > 0 AND CustomerID IS NOT NULL
    GROUP BY CustomerID, Description
    HAVING purchase_count > 1
) AS repeat_buyers
GROUP BY Description
ORDER BY repeat_purchase_customers DESC
LIMIT 10
"""
repeat = run_query(conn, all_queries['Q9_repeat_buyers'])
print("\nQ9. Products with Most Repeat Buyers:")
print(repeat.to_string(index=False))

# ── Q10: New vs Returning Customers (CTE) ────────────────────────────────
all_queries['Q10_new_vs_returning'] = """
WITH first_purchase AS (
    SELECT CustomerID, DATE_FORMAT(MIN(InvoiceDate), '%Y-%m') AS first_month
    FROM transactions
    WHERE Quantity > 0 AND CustomerID IS NOT NULL
    GROUP BY CustomerID
),
monthly_customers AS (
    SELECT
        DATE_FORMAT(t.InvoiceDate, '%Y-%m') AS month,
        t.CustomerID,
        fp.first_month
    FROM transactions t
    JOIN first_purchase fp ON t.CustomerID = fp.CustomerID
    WHERE t.Quantity > 0
    GROUP BY month, t.CustomerID, fp.first_month
)
SELECT
    month,
    COUNT(CASE WHEN month = first_month THEN 1 END) AS new_customers,
    COUNT(CASE WHEN month > first_month  THEN 1 END) AS returning_customers
FROM monthly_customers
GROUP BY month
ORDER BY month
"""
new_vs_return = run_query(conn, all_queries['Q10_new_vs_returning'])
print("\nQ10. New vs Returning Customers by Month:")
print(new_vs_return.to_string(index=False))

# Save all queries to a .sql file for MySQL Workbench
with open('retail_queries.sql', 'w') as f:
    f.write("-- Retail Sales Analysis — SQL Queries\n")
    f.write("-- Run these in MySQL Workbench against retail_db\n\n")
    f.write("USE retail_db;\n\n")
    for name, sql in all_queries.items():
        f.write(f"-- {name.replace('_',' ').upper()}\n")
        f.write(sql.strip() + ";\n\n")
print("\n  All queries saved to: retail_queries.sql")


# ─────────────────────────────────────────────────────────────────────────────
# 3. EDA CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("STEP 3: EDA Charts → saving to output_charts/")
print("="*65)

df_clean = df[(df['Quantity'] > 0) & (df['CustomerID'].notna())].copy()

# Chart 1: Monthly Revenue
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(monthly['month'], monthly['revenue']/1000,
       color='#4C72B0', edgecolor='white', alpha=0.85)
ax.plot(monthly['month'], monthly['revenue']/1000,
        color='#DD8452', linewidth=2, marker='o', markersize=5)
ax.set_xlabel('Month'); ax.set_ylabel('Revenue (£ thousands)')
ax.set_title('Monthly Revenue — Dec 2010 to Dec 2011',
             fontsize=13, fontweight='bold', pad=12)
ax.tick_params(axis='x', rotation=45)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '01_monthly_revenue.png')

# Chart 2: Top 10 Products
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(top_products['Description'][::-1],
        top_products['revenue'][::-1]/1000,
        color='#55A868', edgecolor='white', alpha=0.85)
ax.set_xlabel('Revenue (£ thousands)')
ax.set_title('Top 10 Products by Revenue', fontsize=13, fontweight='bold', pad=12)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '02_top_products.png')

# Chart 3: Revenue by Country
fig, ax = plt.subplots(figsize=(8, 4))
bar_c = ['#4C72B0' if c == 'United Kingdom' else '#DD8452'
         for c in country_rev['Country']]
ax.bar(country_rev['Country'], country_rev['revenue']/1000,
       color=bar_c, edgecolor='white', alpha=0.85)
ax.set_ylabel('Revenue (£ thousands)')
ax.set_title('Revenue by Country', fontsize=13, fontweight='bold', pad=12)
ax.tick_params(axis='x', rotation=30)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '03_revenue_by_country.png')

# Chart 4: Revenue by Day of Week
dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
dow_plot  = dow.set_index('day_of_week').reindex(dow_order)['revenue'] / 1000
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(dow_plot.index, dow_plot.values, color='#4C72B0', edgecolor='white', alpha=0.85)
ax.set_ylabel('Revenue (£ thousands)')
ax.set_title('Revenue by Day of Week', fontsize=13, fontweight='bold', pad=12)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '04_revenue_by_dow.png')

# Chart 5: Order Value Distribution
order_vals = df_clean.groupby('InvoiceNo')['Revenue'].sum()
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(order_vals[order_vals < order_vals.quantile(0.95)],
        bins=40, color='#4C72B0', alpha=0.8, edgecolor='white')
ax.axvline(order_vals.mean(),   color='#DD8452', linestyle='--', linewidth=2,
           label=f'Mean: £{order_vals.mean():.2f}')
ax.axvline(order_vals.median(), color='#55A868', linestyle='--', linewidth=2,
           label=f'Median: £{order_vals.median():.2f}')
ax.set_xlabel('Order Value (£)'); ax.set_ylabel('Number of Orders')
ax.set_title('Order Value Distribution', fontsize=13, fontweight='bold', pad=12)
ax.legend(frameon=False); ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '05_order_value_distribution.png')


# ─────────────────────────────────────────────────────────────────────────────
# 4. RFM CUSTOMER SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("STEP 4: RFM Customer Segmentation")
print("="*65)

snapshot_date = df_clean['InvoiceDate'].max() + pd.Timedelta(days=1)

rfm = df_clean.groupby('CustomerID').agg(
    Recency   = ('InvoiceDate', lambda x: (snapshot_date - x.max()).days),
    Frequency = ('InvoiceNo',   'nunique'),
    Monetary  = ('Revenue',     'sum')
).reset_index()

rfm['R_Score'] = pd.qcut(rfm['Recency'],
                          q=4, labels=[4, 3, 2, 1]).astype(int)
rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'),
                          q=4, labels=[1, 2, 3, 4]).astype(int)
rfm['M_Score'] = pd.qcut(rfm['Monetary'].rank(method='first'),
                          q=4, labels=[1, 2, 3, 4]).astype(int)
rfm['RFM_Score'] = rfm['R_Score'] + rfm['F_Score'] + rfm['M_Score']

def segment(row):
    r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
    if r >= 4 and f >= 4 and m >= 4: return 'Champions'
    elif r >= 3 and f >= 3:           return 'Loyal Customers'
    elif r >= 4 and f <= 2:           return 'New Customers'
    elif r >= 3 and f <= 2:           return 'Potential Loyalists'
    elif r == 2 and f >= 3:           return 'At Risk'
    elif r <= 2 and f >= 3:           return 'Cant Lose Them'
    elif r <= 2 and f <= 2:           return 'Lost'
    else:                              return 'Need Attention'

rfm['Segment'] = rfm.apply(segment, axis=1)
rfm.to_csv('rfm_results.csv', index=False)

seg_summary = rfm.groupby('Segment').agg(
    Customers     = ('CustomerID', 'count'),
    Avg_Recency   = ('Recency',    'mean'),
    Avg_Frequency = ('Frequency',  'mean'),
    Avg_Monetary  = ('Monetary',   'mean'),
    Total_Revenue = ('Monetary',   'sum')
).round(1).sort_values('Total_Revenue', ascending=False)
print("  Segment breakdown:")
print(seg_summary.to_string())
print(f"\n  RFM results saved: rfm_results.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 5. RFM CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("STEP 5: RFM Charts → saving to output_charts/")
print("="*65)

seg_colors = {
    'Champions':           '#2ecc71',
    'Loyal Customers':     '#27ae60',
    'Potential Loyalists': '#3498db',
    'New Customers':       '#9b59b6',
    'At Risk':             '#e67e22',
    'Cant Lose Them':      '#e74c3c',
    'Need Attention':      '#f39c12',
    'Lost':                '#95a5a6',
}

# Chart 6: Customer Segments
seg_counts = rfm['Segment'].value_counts()
colors6 = [seg_colors.get(s, '#4C72B0') for s in seg_counts.index]
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(seg_counts.index[::-1], seg_counts.values[::-1],
               color=colors6[::-1], edgecolor='white', height=0.6)
for bar, val in zip(bars, seg_counts.values[::-1]):
    ax.text(val + 10, bar.get_y() + bar.get_height()/2,
            f'{val:,}', va='center', fontsize=9)
ax.set_xlabel('Number of Customers')
ax.set_title('RFM Customer Segmentation', fontsize=13, fontweight='bold', pad=12)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '06_rfm_segments.png')

# Chart 7: Revenue by Segment
seg_rev = rfm.groupby('Segment')['Monetary'].sum().sort_values(ascending=False)
colors7 = [seg_colors.get(s, '#4C72B0') for s in seg_rev.index]
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.barh(seg_rev.index[::-1], seg_rev.values[::-1]/1000,
               color=colors7[::-1], edgecolor='white', height=0.6)
for bar, val in zip(bars, seg_rev.values[::-1]/1000):
    ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
            f'£{val:.1f}K', va='center', fontsize=9)
ax.set_xlabel('Total Revenue (£ thousands)')
ax.set_title('Revenue Contribution by Customer Segment',
             fontsize=13, fontweight='bold', pad=12)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '07_revenue_by_segment.png')

# Chart 8: RFM Distributions
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, col, color, label in zip(
    axes,
    ['Recency', 'Frequency', 'Monetary'],
    ['#4C72B0', '#55A868', '#DD8452'],
    ['Days Since Last Purchase', 'Number of Orders', 'Total Spend (£)']
):
    ax.hist(rfm[col], bins=30, color=color, alpha=0.8, edgecolor='white')
    ax.set_title(col, fontsize=11, fontweight='bold')
    ax.set_xlabel(label, fontsize=9)
    ax.set_ylabel('Customers')
    ax.spines[['top', 'right']].set_visible(False)
plt.suptitle('RFM Distributions', fontsize=13, fontweight='bold', y=1.02)
plt.tight_layout()
save(fig, '08_rfm_distributions.png')

# Chart 9: New vs Returning Customers
fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(len(new_vs_return))
w = 0.4
ax.bar(x - w/2, new_vs_return['new_customers'],       w,
       label='New Customers',       color='#4C72B0', edgecolor='white', alpha=0.85)
ax.bar(x + w/2, new_vs_return['returning_customers'], w,
       label='Returning Customers', color='#55A868', edgecolor='white', alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(new_vs_return['month'], rotation=45)
ax.set_ylabel('Number of Customers')
ax.set_title('New vs Returning Customers by Month',
             fontsize=13, fontweight='bold', pad=12)
ax.legend(frameon=False)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '09_new_vs_returning.png')

# Chart 10: Pareto — Revenue Concentration
cust_sorted = rfm.sort_values('Monetary', ascending=False).reset_index(drop=True)
cust_sorted['cum_rev_pct'] = cust_sorted['Monetary'].cumsum() / cust_sorted['Monetary'].sum() * 100
cust_sorted['cust_pct']    = (cust_sorted.index + 1) / len(cust_sorted) * 100
idx_80 = (cust_sorted['cum_rev_pct'] >= 80).idxmax()
x_80   = cust_sorted.loc[idx_80, 'cust_pct']
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(cust_sorted['cust_pct'], cust_sorted['cum_rev_pct'],
        color='#4C72B0', linewidth=2.5)
ax.fill_between(cust_sorted['cust_pct'], cust_sorted['cum_rev_pct'],
                alpha=0.1, color='#4C72B0')
ax.axhline(80, color='#DD8452', linestyle='--', alpha=0.7, linewidth=1.5,
           label='80% of revenue')
ax.axvline(x_80, color='#55A868', linestyle='--', alpha=0.7, linewidth=1.5,
           label=f'Top {x_80:.0f}% of customers')
ax.set_xlabel('Cumulative % of Customers')
ax.set_ylabel('Cumulative % of Revenue')
ax.set_title('Pareto Chart — Customer Revenue Concentration',
             fontsize=13, fontweight='bold', pad=12)
ax.legend(frameon=False)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
save(fig, '10_pareto_chart.png')


# ─────────────────────────────────────────────────────────────────────────────
# 6. BUSINESS RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("BUSINESS RECOMMENDATIONS")
print("="*65)

champ_count   = (rfm['Segment'] == 'Champions').sum()
champ_rev     = rfm[rfm['Segment'] == 'Champions']['Monetary'].sum()
at_risk_count = (rfm['Segment'] == 'At Risk').sum()
lost_count    = (rfm['Segment'] == 'Lost').sum()
intl_rev_pct  = country_rev[country_rev['Country'] != 'United Kingdom']['revenue'].sum() \
                / country_rev['revenue'].sum() * 100

print(f"""
1. PROTECT CHAMPIONS ({champ_count:,} customers → £{champ_rev:,.0f} revenue)
   These customers buy frequently, recently, and spend the most.
   Action: VIP loyalty programme, early access to new products,
           personal thank-you communications.

2. RE-ENGAGE AT RISK CUSTOMERS ({at_risk_count:,} customers)
   Used to buy regularly but haven't purchased recently.
   Action: Targeted win-back email with a limited-time discount.
           Do this before they become "Lost."

3. CAPITALISE ON SEASONAL PEAKS (Nov-Dec = highest revenue months)
   Revenue spikes sharply in Q4. January drops significantly.
   Action: Build inventory early, run promotions in Sept-Oct to
           smooth demand. Plan a January clearance campaign.

4. GROW INTERNATIONAL REVENUE (currently {intl_rev_pct:.0f}% of total)
   Germany and France are the top international markets.
   Action: Localised marketing and currency/shipping offers
           for DE and FR customers.

5. ADDRESS {lost_count:,} LOST CUSTOMERS
   Large segment with low recency and frequency.
   Action: One re-engagement campaign with a strong incentive.
           Those who don't respond should be suppressed from
           marketing lists to reduce costs.

6. PARETO INSIGHT: Top {x_80:.0f}% of customers → 80% of revenue
   Action: Any retention investment should prioritise the
           top quartile — losing one Champion costs more than
           losing 10 low-value customers.
""")

print("="*65)
print(f"Done! {len(os.listdir(OUTPUT_DIR))} charts saved to '{OUTPUT_DIR}/' folder.")
print("SQL queries saved to 'retail_queries.sql'")
print("RFM results saved to 'rfm_results.csv'")
print("="*65)

cursor.close()
conn.close()
