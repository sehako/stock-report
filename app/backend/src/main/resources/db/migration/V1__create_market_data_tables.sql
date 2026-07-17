CREATE TABLE stock (
    id BIGSERIAL PRIMARY KEY,
    market VARCHAR(20) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(255) NOT NULL,
    tracked BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uk_stock_market_stock_code UNIQUE (market, stock_code),
    CONSTRAINT chk_stock_market CHECK (market IN ('KOSPI', 'KOSDAQ'))
);

CREATE TABLE stock_price (
    id BIGSERIAL PRIMARY KEY,
    stock_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(19, 4) NOT NULL,
    high_price NUMERIC(19, 4) NOT NULL,
    low_price NUMERIC(19, 4) NOT NULL,
    close_price NUMERIC(19, 4) NOT NULL,
    volume BIGINT NOT NULL,
    change_rate NUMERIC(10, 4),
    CONSTRAINT fk_stock_price_stock FOREIGN KEY (stock_id) REFERENCES stock (id),
    CONSTRAINT uk_stock_price_stock_trade_date UNIQUE (stock_id, trade_date)
);

CREATE TABLE market_index_price (
    id BIGSERIAL PRIMARY KEY,
    index_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(19, 4) NOT NULL,
    high_price NUMERIC(19, 4) NOT NULL,
    low_price NUMERIC(19, 4) NOT NULL,
    close_price NUMERIC(19, 4) NOT NULL,
    volume BIGINT NOT NULL,
    change_rate NUMERIC(10, 4),
    CONSTRAINT uk_market_index_price_index_trade_date UNIQUE (index_code, trade_date),
    CONSTRAINT chk_market_index_price_index_code CHECK (index_code IN ('KOSPI', 'KOSDAQ'))
);

CREATE INDEX idx_stock_tracked_market ON stock (tracked, market);
