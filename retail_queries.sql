-- Retail Sales Analysis — SQL Queries
-- Run these in MySQL Workbench against retail_db

USE retail_db;

-- Q1 TOTAL REVENUE
SELECT ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue
FROM transactions
WHERE Quantity > 0;

-- Q2 MONTHLY REVENUE
SELECT
    DATE_FORMAT(InvoiceDate, '%Y-%m')     AS month,
    ROUND(SUM(Quantity * UnitPrice), 2)   AS revenue,
    COUNT(DISTINCT InvoiceNo)             AS orders,
    COUNT(DISTINCT CustomerID)            AS unique_customers
FROM transactions
WHERE Quantity > 0
GROUP BY month
ORDER BY month;

-- Q3 TOP PRODUCTS
SELECT
    Description,
    SUM(Quantity)                        AS units_sold,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY Description
ORDER BY revenue DESC
LIMIT 10;

-- Q4 REVENUE BY COUNTRY
SELECT
    Country,
    COUNT(DISTINCT CustomerID)           AS customers,
    COUNT(DISTINCT InvoiceNo)            AS orders,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY Country
ORDER BY revenue DESC
LIMIT 8;

-- Q5 AVG ORDER VALUE
SELECT
    ROUND(AVG(order_value), 2) AS avg_order_value,
    ROUND(MIN(order_value), 2) AS min_order_value,
    ROUND(MAX(order_value), 2) AS max_order_value
FROM (
    SELECT InvoiceNo, SUM(Quantity * UnitPrice) AS order_value
    FROM transactions
    WHERE Quantity > 0
    GROUP BY InvoiceNo
) AS order_totals;

-- Q6 TOP CUSTOMERS
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
LIMIT 10;

-- Q7 DAY OF WEEK
SELECT
    DAYNAME(InvoiceDate)                 AS day_of_week,
    COUNT(DISTINCT InvoiceNo)            AS orders,
    ROUND(SUM(Quantity * UnitPrice), 2)  AS revenue
FROM transactions
WHERE Quantity > 0
GROUP BY DAYNAME(InvoiceDate), DAYOFWEEK(InvoiceDate)
ORDER BY DAYOFWEEK(InvoiceDate);

-- Q8 CANCELLATION RATE
SELECT
    COUNT(CASE WHEN Quantity < 0 THEN 1 END)  AS cancelled_rows,
    COUNT(CASE WHEN Quantity > 0 THEN 1 END)  AS normal_rows,
    ROUND(
        COUNT(CASE WHEN Quantity < 0 THEN 1 END) * 100.0 / COUNT(*), 2
    ) AS cancellation_rate_pct
FROM transactions;

-- Q9 REPEAT BUYERS
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
LIMIT 10;

-- Q10 NEW VS RETURNING
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
ORDER BY month;

