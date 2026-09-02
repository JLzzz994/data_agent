-- 慧经营智能问数 Demo DW。
-- tenant_id / shop_id 中的权限字段故意不写入 conf/meta_config.yaml，
-- 避免 LLM 参与权限判断；它们只由 scoped_sql.py 确定性注入。

DROP TABLE IF EXISTS fact_after_sale;
DROP TABLE IF EXISTS fact_purchase;
DROP TABLE IF EXISTS fact_inventory_snapshot;
DROP TABLE IF EXISTS fact_trade_order;
DROP TABLE IF EXISTS dim_warehouse;
DROP TABLE IF EXISTS dim_goods;
DROP TABLE IF EXISTS dim_shop;

CREATE TABLE dim_shop (
    tenant_id VARCHAR(64) NOT NULL,
    shop_id VARCHAR(64) NOT NULL,
    shop_name VARCHAR(128) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    PRIMARY KEY (tenant_id, shop_id)
);

CREATE TABLE dim_goods (
    tenant_id VARCHAR(64) NOT NULL,
    goods_id VARCHAR(64) NOT NULL,
    goods_no VARCHAR(64) NOT NULL,
    goods_name VARCHAR(128) NOT NULL,
    brand VARCHAR(64) NOT NULL,
    category VARCHAR(64) NOT NULL,
    PRIMARY KEY (tenant_id, goods_id)
);

CREATE TABLE dim_warehouse (
    tenant_id VARCHAR(64) NOT NULL,
    warehouse_id VARCHAR(64) NOT NULL,
    warehouse_name VARCHAR(128) NOT NULL,
    warehouse_region VARCHAR(64) NOT NULL,
    PRIMARY KEY (tenant_id, warehouse_id)
);

CREATE TABLE fact_trade_order (
    tenant_id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    shop_id VARCHAR(64) NOT NULL,
    goods_id VARCHAR(64) NOT NULL,
    warehouse_id VARCHAR(64) NOT NULL,
    pay_time DATETIME NOT NULL,
    order_status VARCHAR(32) NOT NULL,
    quantity INT NOT NULL,
    goods_amount DECIMAL(18,2) NOT NULL,
    discount_amount DECIMAL(18,2) NOT NULL,
    paid_amount DECIMAL(18,2) NOT NULL,
    refund_amount DECIMAL(18,2) NOT NULL,
    cost_amount DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (tenant_id, order_id),
    INDEX idx_trade_scope (tenant_id, shop_id, pay_time)
);

CREATE TABLE fact_inventory_snapshot (
    tenant_id VARCHAR(64) NOT NULL,
    shop_id VARCHAR(64) NOT NULL,
    snapshot_date DATE NOT NULL,
    warehouse_id VARCHAR(64) NOT NULL,
    goods_id VARCHAR(64) NOT NULL,
    available_qty INT NOT NULL,
    occupied_qty INT NOT NULL,
    in_transit_qty INT NOT NULL,
    inventory_amount DECIMAL(18,2) NOT NULL,
    INDEX idx_inventory_scope (tenant_id, shop_id, snapshot_date)
);

CREATE TABLE fact_purchase (
    tenant_id VARCHAR(64) NOT NULL,
    shop_id VARCHAR(64) NOT NULL,
    purchase_id VARCHAR(64) NOT NULL,
    goods_id VARCHAR(64) NOT NULL,
    warehouse_id VARCHAR(64) NOT NULL,
    purchase_time DATETIME NOT NULL,
    purchase_qty INT NOT NULL,
    purchase_amount DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (tenant_id, purchase_id),
    INDEX idx_purchase_scope (tenant_id, shop_id, purchase_time)
);

CREATE TABLE fact_after_sale (
    tenant_id VARCHAR(64) NOT NULL,
    shop_id VARCHAR(64) NOT NULL,
    after_sale_id VARCHAR(64) NOT NULL,
    order_id VARCHAR(64) NOT NULL,
    after_sale_time DATETIME NOT NULL,
    after_sale_type VARCHAR(32) NOT NULL,
    after_sale_status VARCHAR(32) NOT NULL,
    confirmed_refund_amount DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (tenant_id, after_sale_id),
    INDEX idx_after_sale_scope (tenant_id, shop_id, after_sale_time)
);

INSERT INTO dim_shop VALUES
('tenant_hc_001', 'shop_tmall_001', '华策旗舰店', '天猫'),
('tenant_hc_001', 'shop_jd_001', '华策京东店', '京东'),
('tenant_other_001', 'shop_other_001', '其他商家旗舰店', '天猫');

INSERT INTO dim_goods VALUES
('tenant_hc_001', 'goods_001', 'HC-1001', '轻羽冲锋衣', '北川', '户外服饰'),
('tenant_hc_001', 'goods_002', 'HC-1002', '城市双肩包', '北川', '箱包'),
('tenant_hc_001', 'goods_003', 'HC-1003', '保温随行杯', '山屿', '家居'),
('tenant_other_001', 'goods_901', 'OT-9001', '其他租户商品', '其他品牌', '其他类目');

INSERT INTO dim_warehouse VALUES
('tenant_hc_001', 'wh_east_001', '华东一号仓', '华东'),
('tenant_hc_001', 'wh_south_001', '华南一号仓', '华南'),
('tenant_other_001', 'wh_other_001', '其他租户仓', '华东');

INSERT INTO fact_trade_order VALUES
('tenant_hc_001', 'ord_001', 'shop_tmall_001', 'goods_001', 'wh_east_001', '2026-08-10 10:15:00', 'PAID', 2, 798.00, 80.00, 718.00, 0.00, 360.00),
('tenant_hc_001', 'ord_002', 'shop_tmall_001', 'goods_002', 'wh_east_001', '2026-08-18 14:20:00', 'PAID', 1, 399.00, 40.00, 359.00, 100.00, 180.00),
('tenant_hc_001', 'ord_003', 'shop_tmall_001', 'goods_003', 'wh_south_001', '2026-08-27 09:05:00', 'PAID', 3, 297.00, 20.00, 277.00, 0.00, 120.00),
('tenant_hc_001', 'ord_004', 'shop_jd_001', 'goods_001', 'wh_south_001', '2026-08-15 18:35:00', 'PAID', 1, 399.00, 30.00, 369.00, 0.00, 180.00),
('tenant_hc_001', 'ord_005', 'shop_jd_001', 'goods_002', 'wh_east_001', '2026-08-29 21:10:00', 'PAID', 2, 798.00, 100.00, 698.00, 200.00, 360.00),
('tenant_hc_001', 'ord_006', 'shop_jd_001', 'goods_003', 'wh_east_001', '2026-09-01 11:00:00', 'PAID', 5, 495.00, 50.00, 445.00, 0.00, 200.00),
('tenant_other_001', 'ord_901', 'shop_other_001', 'goods_901', 'wh_other_001', '2026-08-30 12:00:00', 'PAID', 99, 99999.00, 0.00, 99999.00, 0.00, 100.00);

INSERT INTO fact_inventory_snapshot VALUES
('tenant_hc_001', 'shop_tmall_001', '2026-09-01', 'wh_east_001', 'goods_001', 18, 4, 20, 3240.00),
('tenant_hc_001', 'shop_tmall_001', '2026-09-01', 'wh_east_001', 'goods_002', 7, 3, 10, 1260.00),
('tenant_hc_001', 'shop_jd_001', '2026-09-01', 'wh_south_001', 'goods_001', 6, 2, 12, 1080.00),
('tenant_hc_001', 'shop_jd_001', '2026-09-01', 'wh_south_001', 'goods_003', 30, 5, 0, 1200.00),
('tenant_other_001', 'shop_other_001', '2026-09-01', 'wh_other_001', 'goods_901', 9999, 0, 0, 1.00);

INSERT INTO fact_purchase VALUES
('tenant_hc_001', 'shop_tmall_001', 'po_001', 'goods_001', 'wh_east_001', '2026-08-05 09:00:00', 100, 18000.00),
('tenant_hc_001', 'shop_tmall_001', 'po_002', 'goods_002', 'wh_east_001', '2026-08-20 10:00:00', 50, 9000.00),
('tenant_hc_001', 'shop_jd_001', 'po_003', 'goods_003', 'wh_south_001', '2026-08-25 16:00:00', 80, 3200.00),
('tenant_other_001', 'shop_other_001', 'po_901', 'goods_901', 'wh_other_001', '2026-08-25 16:00:00', 9999, 1.00);

INSERT INTO fact_after_sale VALUES
('tenant_hc_001', 'shop_tmall_001', 'as_001', 'ord_002', '2026-08-20 10:30:00', '仅退款', 'COMPLETED', 100.00),
('tenant_hc_001', 'shop_jd_001', 'as_002', 'ord_005', '2026-08-31 15:00:00', '退货退款', 'COMPLETED', 200.00),
('tenant_hc_001', 'shop_tmall_001', 'as_003', 'ord_003', '2026-09-01 08:30:00', '换货', 'PROCESSING', 0.00),
('tenant_other_001', 'shop_other_001', 'as_901', 'ord_901', '2026-08-31 10:00:00', '仅退款', 'COMPLETED', 99999.00);
