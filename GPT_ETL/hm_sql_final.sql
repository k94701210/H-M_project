USE HM_Analytics;
GO

/*====================================================
1) STAGING TABLES
你已經把 stg_articles 的代碼欄位改成 VARCHAR
下面是完整建議版
====================================================*/

IF OBJECT_ID('dbo.stg_articles', 'U') IS NOT NULL DROP TABLE dbo.stg_articles;
CREATE TABLE dbo.stg_articles (
    article_id                      VARCHAR(20),
    product_code                    VARCHAR(20),
    prod_name                       NVARCHAR(255),
    product_type_no                 VARCHAR(50),
    product_type_name               NVARCHAR(255),
    product_group_name              NVARCHAR(255),
    graphical_appearance_no         VARCHAR(50),
    graphical_appearance_name       NVARCHAR(255),
    colour_group_code               VARCHAR(50),
    colour_group_name               NVARCHAR(255),
    perceived_colour_value_id       VARCHAR(50),
    perceived_colour_value_name     NVARCHAR(255),
    perceived_colour_master_id      VARCHAR(50),
    perceived_colour_master_name    NVARCHAR(255),
    department_no                   VARCHAR(50),
    department_name                 NVARCHAR(255),
    index_code                      VARCHAR(20),
    index_name                      NVARCHAR(255),
    index_group_no                  VARCHAR(50),
    index_group_name                NVARCHAR(255),
    section_no                      VARCHAR(50),
    section_name                    NVARCHAR(255),
    garment_group_no                VARCHAR(50),
    garment_group_name              NVARCHAR(255),
    detail_desc                     NVARCHAR(MAX),
    load_time                       DATETIME2 DEFAULT SYSDATETIME()
);
GO

IF OBJECT_ID('dbo.stg_customers', 'U') IS NOT NULL DROP TABLE dbo.stg_customers;
CREATE TABLE dbo.stg_customers (
    customer_id              VARCHAR(100),
    FN                       VARCHAR(20),
    Active                   VARCHAR(20),
    club_member_status       NVARCHAR(100),
    fashion_news_frequency   NVARCHAR(100),
    age                      INT,
    postal_code              VARCHAR(100),
    load_time                DATETIME2 DEFAULT SYSDATETIME()
);
GO

IF OBJECT_ID('dbo.stg_transactions', 'U') IS NOT NULL DROP TABLE dbo.stg_transactions;
CREATE TABLE dbo.stg_transactions (
    t_dat              DATE,
    customer_id        VARCHAR(100),
    article_id         VARCHAR(20),
    price              DECIMAL(18,10),
    sales_channel_id   TINYINT,
    batch_id           INT,
    row_num_in_batch   INT,
    load_time          DATETIME2 DEFAULT SYSDATETIME()
);
GO


/*====================================================
2) DIM / FACT TABLES
dim_customers 不做年齡分層
====================================================*/

IF OBJECT_ID('dbo.dim_articles', 'U') IS NOT NULL DROP TABLE dbo.dim_articles;
CREATE TABLE dbo.dim_articles (
    article_sk                      INT IDENTITY(1,1) PRIMARY KEY,
    article_id                      VARCHAR(20) NOT NULL,
    product_code                    VARCHAR(20),
    prod_name                       NVARCHAR(255),
    product_type_no                 INT NULL,
    product_type_name               NVARCHAR(255),
    product_group_name              NVARCHAR(255),
    graphical_appearance_no         INT NULL,
    graphical_appearance_name       NVARCHAR(255),
    colour_group_code               INT NULL,
    colour_group_name               NVARCHAR(255),
    perceived_colour_value_id       INT NULL,
    perceived_colour_value_name     NVARCHAR(255),
    perceived_colour_master_id      INT NULL,
    perceived_colour_master_name    NVARCHAR(255),
    department_no                   INT NULL,
    department_name                 NVARCHAR(255),
    index_code                      VARCHAR(20),
    index_name                      NVARCHAR(255),
    index_group_no                  INT NULL,
    index_group_name                NVARCHAR(255),
    section_no                      INT NULL,
    section_name                    NVARCHAR(255),
    garment_group_no                INT NULL,
    garment_group_name              NVARCHAR(255),
    detail_desc                     NVARCHAR(MAX)
);
GO

IF OBJECT_ID('dbo.dim_customers', 'U') IS NOT NULL DROP TABLE dbo.dim_customers;
CREATE TABLE dbo.dim_customers (
    customer_sk               INT IDENTITY(1,1) PRIMARY KEY,
    customer_id               VARCHAR(100) NOT NULL,
    FN                        VARCHAR(20),
    Active                    VARCHAR(20),
    club_member_status        NVARCHAR(100),
    fashion_news_frequency    NVARCHAR(100),
    age                       INT,
    postal_code               VARCHAR(100)
);
GO

IF OBJECT_ID('dbo.fact_transactions', 'U') IS NOT NULL DROP TABLE dbo.fact_transactions;
CREATE TABLE dbo.fact_transactions (
    transaction_sk        BIGINT IDENTITY(1,1) PRIMARY KEY,
    transaction_date      DATE NOT NULL,
    customer_id           VARCHAR(100) NOT NULL,
    article_id            VARCHAR(20) NOT NULL,
    price                 DECIMAL(18,10) NOT NULL,
    price_amount          DECIMAL(18,2) NULL,
    sales_channel_id      TINYINT,
    transaction_year      INT,
    transaction_month     INT,
    transaction_ym        CHAR(7),
    load_time             DATETIME2 DEFAULT SYSDATETIME()
);
GO


/*====================================================
3) STAGING -> DIM / FACT
====================================================*/

TRUNCATE TABLE dbo.dim_articles;

INSERT INTO dbo.dim_articles (
    article_id, product_code, prod_name, product_type_no, product_type_name,
    product_group_name, graphical_appearance_no, graphical_appearance_name,
    colour_group_code, colour_group_name, perceived_colour_value_id,
    perceived_colour_value_name, perceived_colour_master_id, perceived_colour_master_name,
    department_no, department_name, index_code, index_name, index_group_no,
    index_group_name, section_no, section_name, garment_group_no,
    garment_group_name, detail_desc
)
SELECT DISTINCT
    article_id,
    product_code,
    prod_name,
    TRY_CAST(product_type_no AS INT),
    product_type_name,
    product_group_name,
    TRY_CAST(graphical_appearance_no AS INT),
    graphical_appearance_name,
    TRY_CAST(colour_group_code AS INT),
    colour_group_name,
    TRY_CAST(perceived_colour_value_id AS INT),
    perceived_colour_value_name,
    TRY_CAST(perceived_colour_master_id AS INT),
    perceived_colour_master_name,
    TRY_CAST(department_no AS INT),
    department_name,
    index_code,
    index_name,
    TRY_CAST(index_group_no AS INT),
    index_group_name,
    TRY_CAST(section_no AS INT),
    section_name,
    TRY_CAST(garment_group_no AS INT),
    garment_group_name,
    detail_desc
FROM dbo.stg_articles;
GO

TRUNCATE TABLE dbo.dim_customers;

INSERT INTO dbo.dim_customers (
    customer_id, FN, Active, club_member_status,
    fashion_news_frequency, age, postal_code
)
SELECT DISTINCT
    customer_id,
    FN,
    Active,
    club_member_status,
    fashion_news_frequency,
    age,
    postal_code
FROM dbo.stg_customers;
GO

TRUNCATE TABLE dbo.fact_transactions;

INSERT INTO dbo.fact_transactions (
    transaction_date,
    customer_id,
    article_id,
    price,
    price_amount,
    sales_channel_id,
    transaction_year,
    transaction_month,
    transaction_ym
)
SELECT
    t_dat AS transaction_date,
    customer_id,
    article_id,
    price,
    CAST(price * 1000.0 AS DECIMAL(18,2)) AS price_amount,
    sales_channel_id,
    YEAR(t_dat) AS transaction_year,
    MONTH(t_dat) AS transaction_month,
    CONVERT(CHAR(7), t_dat, 120) AS transaction_ym
FROM dbo.stg_transactions;
GO


/*====================================================
4) INDEXES
====================================================*/

CREATE UNIQUE INDEX IX_dim_articles_article_id
ON dbo.dim_articles(article_id);
GO

CREATE UNIQUE INDEX IX_dim_customers_customer_id
ON dbo.dim_customers(customer_id);
GO

CREATE INDEX IX_fact_transactions_date
ON dbo.fact_transactions(transaction_date);
GO

CREATE INDEX IX_fact_transactions_customer
ON dbo.fact_transactions(customer_id);
GO

CREATE INDEX IX_fact_transactions_article
ON dbo.fact_transactions(article_id);
GO

CREATE INDEX IX_fact_transactions_ym
ON dbo.fact_transactions(transaction_ym);
GO

CREATE INDEX IX_fact_transactions_channel
ON dbo.fact_transactions(sales_channel_id);
GO


/*====================================================
5) AGG TABLES
====================================================*/

IF OBJECT_ID('dbo.agg_sales_monthly', 'U') IS NOT NULL DROP TABLE dbo.agg_sales_monthly;

SELECT
    transaction_ym,
    sales_channel_id,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT customer_id) AS customer_count,
    COUNT(DISTINCT article_id) AS article_count,
    SUM(price_amount) AS total_sales_amount,
    AVG(price_amount) AS avg_price_amount
INTO dbo.agg_sales_monthly
FROM dbo.fact_transactions
GROUP BY transaction_ym, sales_channel_id;
GO

IF OBJECT_ID('dbo.agg_article_monthly', 'U') IS NOT NULL DROP TABLE dbo.agg_article_monthly;

SELECT
    f.transaction_ym,
    f.article_id,
    a.prod_name,
    a.product_group_name,
    a.product_type_name,
    a.colour_group_name,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT f.customer_id) AS customer_count,
    SUM(f.price_amount) AS total_sales_amount
INTO dbo.agg_article_monthly
FROM dbo.fact_transactions f
LEFT JOIN dbo.dim_articles a
    ON f.article_id = a.article_id
GROUP BY
    f.transaction_ym,
    f.article_id,
    a.prod_name,
    a.product_group_name,
    a.product_type_name,
    a.colour_group_name;
GO

IF OBJECT_ID('dbo.agg_customer_monthly', 'U') IS NOT NULL DROP TABLE dbo.agg_customer_monthly;

SELECT
    f.transaction_ym,
    f.customer_id,
    c.age,
    c.club_member_status,
    c.fashion_news_frequency,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT f.article_id) AS article_count,
    SUM(f.price_amount) AS total_sales_amount,
    AVG(f.price_amount) AS avg_price_amount
INTO dbo.agg_customer_monthly
FROM dbo.fact_transactions f
LEFT JOIN dbo.dim_customers c
    ON f.customer_id = c.customer_id
GROUP BY
    f.transaction_ym,
    f.customer_id,
    c.age,
    c.club_member_status,
    c.fashion_news_frequency;
GO


/*====================================================
6) 驗證用 SQL
====================================================*/

SELECT COUNT(*) AS stg_articles_count FROM dbo.stg_articles;
SELECT COUNT(*) AS stg_customers_count FROM dbo.stg_customers;
SELECT COUNT(*) AS stg_transactions_count FROM dbo.stg_transactions;

SELECT COUNT(*) AS dim_articles_count FROM dbo.dim_articles;
SELECT COUNT(*) AS dim_customers_count FROM dbo.dim_customers;
SELECT COUNT(*) AS fact_transactions_count FROM dbo.fact_transactions;

SELECT TOP 10 * FROM dbo.agg_sales_monthly ORDER BY transaction_ym;
GO
