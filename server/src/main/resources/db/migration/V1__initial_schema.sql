create table stock (
    id bigserial primary key,
    stock_code varchar(32) not null,
    stock_name varchar(255) not null,
    market varchar(16) not null,
    industry_name varchar(255),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_stock_stock_code unique (stock_code),
    constraint ck_stock_market check (market in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN'))
);

create table report_revision (
    id bigserial primary key,
    report_date date not null,
    revision_no integer not null,
    revision_type varchar(16) not null,
    is_active boolean not null,
    calculation_version varchar(64) not null,
    target_stock_count integer,
    completed_stock_count integer,
    failed_stock_count integer,
    insufficient_stock_count integer,
    no_trading_stock_count integer,
    created_at timestamptz not null default now(),
    published_at timestamptz,
    constraint uq_report_revision_report_date_revision_no unique (report_date, revision_no),
    constraint uq_report_revision_id_report_date unique (id, report_date),
    constraint ck_report_revision_revision_type check (revision_type in ('INITIAL', 'FINAL', 'CORRECTION')),
    constraint ck_report_revision_revision_no check (revision_no >= 1),
    constraint ck_report_revision_target_stock_count check (target_stock_count is null or target_stock_count >= 0),
    constraint ck_report_revision_completed_stock_count check (completed_stock_count is null or completed_stock_count >= 0),
    constraint ck_report_revision_failed_stock_count check (failed_stock_count is null or failed_stock_count >= 0),
    constraint ck_report_revision_insufficient_stock_count check (insufficient_stock_count is null or insufficient_stock_count >= 0),
    constraint ck_report_revision_no_trading_stock_count check (no_trading_stock_count is null or no_trading_stock_count >= 0)
);

create unique index ux_report_revision_active_report_date
    on report_revision (report_date)
    where is_active = true;

create table batch_job_run (
    id bigserial primary key,
    report_date date not null,
    status varchar(32) not null,
    started_at timestamptz,
    finished_at timestamptz,
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_batch_job_run_report_date unique (report_date),
    constraint uq_batch_job_run_id_report_date unique (id, report_date),
    constraint ck_batch_job_run_status check (
        status in (
            'RUNNING',
            'PUBLISHED_INITIAL',
            'RETRYING',
            'PUBLISHED_FINAL',
            'FAILED',
            'DELAYED',
            'SKIPPED_MARKET_CLOSED'
        )
    )
);

create index ix_batch_job_run_report_date on batch_job_run (report_date);
create index ix_batch_job_run_report_date_status on batch_job_run (report_date, status);

create table daily_price (
    id bigserial primary key,
    stock_id bigint not null,
    trade_date date not null,
    open_price numeric(18, 4),
    high_price numeric(18, 4),
    low_price numeric(18, 4),
    close_price numeric(18, 4),
    volume bigint,
    change_rate numeric(18, 8),
    trade_value numeric(24, 2),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_daily_price_stock foreign key (stock_id) references stock (id),
    constraint uq_daily_price_stock_id_trade_date unique (stock_id, trade_date)
);

create table daily_indicator (
    id bigserial primary key,
    stock_id bigint not null,
    trade_date date not null,
    calculation_version varchar(64) not null,
    macd_line numeric(18, 8),
    macd_signal numeric(18, 8),
    macd_histogram numeric(18, 8),
    stoch_macd_k numeric(18, 8),
    stoch_macd_d numeric(18, 8),
    ma5 numeric(18, 8),
    ma20 numeric(18, 8),
    ma60 numeric(18, 8),
    ma120 numeric(18, 8),
    ma240 numeric(18, 8),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_daily_indicator_stock foreign key (stock_id) references stock (id),
    constraint uq_daily_indicator_stock_id_trade_date_calculation_version unique (stock_id, trade_date, calculation_version)
);

create table market_index_price (
    id bigserial primary key,
    index_code varchar(16) not null,
    trade_date date not null,
    open_price numeric(18, 4),
    high_price numeric(18, 4),
    low_price numeric(18, 4),
    close_price numeric(18, 4),
    volume bigint,
    change_rate numeric(18, 8),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint uq_market_index_price_index_code_trade_date unique (index_code, trade_date),
    constraint ck_market_index_price_index_code check (index_code in ('KOSPI', 'KOSDAQ'))
);

create table signal_event (
    id bigserial primary key,
    stock_id bigint not null,
    signal_type varchar(64) not null,
    cross_date date not null,
    calculation_version varchar(64) not null,
    stoch_macd_k numeric(18, 8),
    stoch_macd_d numeric(18, 8),
    created_at timestamptz not null default now(),
    constraint fk_signal_event_stock foreign key (stock_id) references stock (id),
    constraint uq_signal_event_stock_id_signal_type_cross_date_calculation_version
        unique (stock_id, signal_type, cross_date, calculation_version),
    constraint ck_signal_event_signal_type check (signal_type in ('STOCH_MACD_GOLDEN_CROSS'))
);

create index ix_signal_event_cross_date_calculation_version
    on signal_event (cross_date, calculation_version);

create table stock_analysis (
    id bigserial primary key,
    report_revision_id bigint not null,
    stock_id bigint not null,
    signal_event_id bigint,
    analysis_status varchar(32) not null,
    stock_name_snapshot varchar(255) not null,
    market_snapshot varchar(16) not null,
    industry_name_snapshot varchar(255),
    selection_rank integer not null,
    selection_volume bigint not null,
    market_cap numeric(24, 2),
    trade_value numeric(24, 2),
    current_price numeric(18, 4),
    last_trade_date date,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_stock_analysis_report_revision foreign key (report_revision_id) references report_revision (id),
    constraint fk_stock_analysis_stock foreign key (stock_id) references stock (id),
    constraint fk_stock_analysis_signal_event foreign key (signal_event_id) references signal_event (id),
    constraint uq_stock_analysis_report_revision_id_stock_id unique (report_revision_id, stock_id),
    constraint ck_stock_analysis_selection_rank check (selection_rank >= 1),
    constraint ck_stock_analysis_analysis_status check (
        analysis_status in (
            'SIGNAL_FOUND',
            'NO_SIGNAL',
            'INSUFFICIENT_DATA',
            'DATA_PREPARING',
            'DATA_UPDATE_FAILED',
            'NO_TRADING_TODAY',
            'ANALYSIS_FAILED'
        )
    ),
    constraint ck_stock_analysis_market_snapshot check (market_snapshot in ('KOSPI', 'KOSDAQ', 'KONEX', 'UNKNOWN'))
);

create index ix_stock_analysis_report_revision_id_analysis_status
    on stock_analysis (report_revision_id, analysis_status);

create index ix_stock_analysis_report_revision_id_selection_rank
    on stock_analysis (report_revision_id, selection_rank);

create table industry_analysis (
    id bigserial primary key,
    report_revision_id bigint not null,
    industry_name varchar(255) not null,
    area_basis varchar(32) not null,
    stock_count integer not null,
    market_cap_sum numeric(24, 2),
    trade_value_sum numeric(24, 2),
    average_change_rate numeric(18, 8),
    signal_count integer not null,
    signal_denominator_count integer not null,
    excluded_count integer not null,
    signal_ratio numeric(18, 8),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_industry_analysis_report_revision foreign key (report_revision_id) references report_revision (id),
    constraint uq_industry_analysis_report_revision_id_industry_name unique (report_revision_id, industry_name),
    constraint ck_industry_analysis_area_basis check (area_basis in ('market_cap', 'trade_value', 'stock_count')),
    constraint ck_industry_analysis_stock_count check (stock_count >= 0),
    constraint ck_industry_analysis_signal_count check (signal_count >= 0),
    constraint ck_industry_analysis_signal_denominator_count check (signal_denominator_count >= 0),
    constraint ck_industry_analysis_excluded_count check (excluded_count >= 0),
    constraint ck_industry_analysis_signal_ratio check (signal_ratio is null or (signal_ratio >= 0 and signal_ratio <= 1))
);

create table market_ai_summary (
    id bigserial primary key,
    report_date date not null,
    report_revision_id bigint not null,
    status varchar(16) not null,
    summary_text text,
    input_hash varchar(128) not null,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_market_ai_summary_report_revision
        foreign key (report_revision_id, report_date) references report_revision (id, report_date),
    constraint uq_market_ai_summary_report_date unique (report_date),
    constraint ck_market_ai_summary_status check (status in ('PENDING', 'RUNNING', 'COMPLETED', 'DELAYED'))
);

create table batch_stock_run (
    id bigserial primary key,
    batch_job_run_id bigint not null,
    stock_id bigint not null,
    report_date date not null,
    status varchar(32) not null,
    attempt_count integer not null,
    next_retry_at timestamptz,
    last_error text,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_batch_stock_run_batch_job_run
        foreign key (batch_job_run_id, report_date) references batch_job_run (id, report_date),
    constraint fk_batch_stock_run_stock foreign key (stock_id) references stock (id),
    constraint uq_batch_stock_run_batch_job_run_id_stock_id unique (batch_job_run_id, stock_id),
    constraint ck_batch_stock_run_attempt_count check (attempt_count >= 0),
    constraint ck_batch_stock_run_status check (status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'RETRYABLE', 'FAILED_PERMANENT'))
);

create index ix_batch_stock_run_report_date_status
    on batch_stock_run (report_date, status);

create index ix_batch_stock_run_batch_job_run_id_status
    on batch_stock_run (batch_job_run_id, status);

create index ix_batch_stock_run_next_retry_at
    on batch_stock_run (next_retry_at);

create table daily_stock_processing_status (
    id bigserial primary key,
    report_date date not null,
    stock_id bigint not null,
    analysis_status varchar(32) not null,
    last_batch_job_run_id bigint,
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_daily_stock_processing_status_stock foreign key (stock_id) references stock (id),
    constraint fk_daily_stock_processing_status_last_batch_job_run
        foreign key (last_batch_job_run_id, report_date) references batch_job_run (id, report_date),
    constraint uq_daily_stock_processing_status_report_date_stock_id unique (report_date, stock_id),
    constraint ck_daily_stock_processing_status_analysis_status check (
        analysis_status in (
            'SIGNAL_FOUND',
            'NO_SIGNAL',
            'INSUFFICIENT_DATA',
            'DATA_PREPARING',
            'DATA_UPDATE_FAILED',
            'NO_TRADING_TODAY',
            'ANALYSIS_FAILED'
        )
    )
);

create index ix_daily_stock_processing_status_report_date_analysis_status
    on daily_stock_processing_status (report_date, analysis_status);
