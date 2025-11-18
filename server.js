const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// --- PASTE YOUR CONNECTION STRING HERE ---
const connectionString = 'postgresql://postgres:Nitya%2307@db.gzcsbmimpdxjgvgtfkuh.supabase.co:5432/postgres';

const pool = new Pool({ connectionString });

const initializeDatabase = async () => {
    try {
        await pool.query('SELECT NOW()');
        await pool.query(`
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, stock INTEGER NOT NULL,
                price NUMERIC(10, 2) NOT NULL, image_url TEXT
            );
        `);
        await pool.query(`
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY, customer_name TEXT NOT NULL, contact_number TEXT,
                delivery_address TEXT, items JSONB NOT NULL, order_date TIMESTAMPTZ NOT NULL,
                status VARCHAR(50) DEFAULT 'Out for Delivery'
            );
        `);
        console.log("✅ 'products' and 'orders' tables are ready.");
    } catch (err) {
        console.error("❌ ERROR initializing database.", err.message);
    }
};

// --- PRODUCT API Endpoints (No change) ---
app.get('/api/products', async (req, res) => { /* ... no change ... */ 
    try {
        const { rows } = await pool.query('SELECT * FROM products ORDER BY id DESC');
        res.json(rows);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
app.post('/api/products', async (req, res) => { /* ... no change ... */ 
    const { name, stock, price, image_url } = req.body;
    try {
        const { rows } = await pool.query( 'INSERT INTO products (name, stock, price, image_url) VALUES ($1, $2, $3, $4) RETURNING *', [name, stock, price, image_url]);
        res.status(201).json(rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
app.get('/api/products/:id', async (req, res) => { /* ... no change ... */ 
    try {
        const { id } = req.params;
        const { rows } = await pool.query('SELECT * FROM products WHERE id = $1', [id]);
        if (rows.length === 0) return res.status(404).json({ error: 'Product not found' });
        res.json(rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
app.put('/api/products/:id', async (req, res) => { /* ... no change ... */ 
    try {
        const { id } = req.params;
        const { name, stock, price, image_url } = req.body;
        const { rows } = await pool.query( 'UPDATE products SET name = $1, stock = $2, price = $3, image_url = $4 WHERE id = $5 RETURNING *', [name, stock, price, image_url, id]);
        res.json(rows[0]);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
app.delete('/api/products/:id', async (req, res) => { /* ... no change ... */ 
    try {
        const { id } = req.params;
        const { rows } = await pool.query('DELETE FROM products WHERE id = $1 RETURNING *', [id]);
        if (rows.length === 0) {
            return res.status(404).json({ error: 'Product not found' });
        }
        res.json({ success: true, message: `Product "${rows[0].name}" deleted.` });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// --- ORDER API Endpoints ---

// POST a new order
app.post('/api/orders', async (req, res) => {
    const { customerName, contactNumber, deliveryAddress, items, orderDate } = req.body;
    const client = await pool.connect();
    try {
        await client.query('BEGIN');
        let totalAmount = 0;
        const itemsWithPrices = [];

        for (const item of items) {
            // Get current price from products table
            const productRes = await client.query('SELECT price FROM products WHERE name = $1', [item.name]);
            if (productRes.rows.length === 0) throw new Error(`Product ${item.name} not found.`);
            
            const price = parseFloat(productRes.rows[0].price);
            totalAmount += price * item.quantity;
            itemsWithPrices.push({ ...item, price }); // Add price to the item

            // Reduce stock
            await client.query(
                'UPDATE products SET stock = stock - $1 WHERE name = $2 AND stock >= $1',
                [item.quantity, item.name]
            );
        }
        
        // Save the new order with enriched item data and total amount
        const { rows } = await client.query(
            'INSERT INTO orders (customer_name, contact_number, delivery_address, items, order_date) VALUES ($1, $2, $3, $4, $5) RETURNING *',
            [customerName, contactNumber, deliveryAddress, JSON.stringify(itemsWithPrices), orderDate]
        );
        
        await client.query('COMMIT');
        res.status(201).json({ success: true, order: rows[0] });
    } catch (err) {
        await client.query('ROLLBACK');
        console.error("Order processing error:", err.message);
        res.status(500).json({ error: 'Failed to process order.' });
    } finally {
        client.release();
    }
});

// GET active and delivered orders
app.get('/api/orders', async (req, res) => {
    try {
        const deliveryRes = await pool.query("SELECT * FROM orders WHERE status = 'Out for Delivery' ORDER BY order_date DESC");
        const deliveredRes = await pool.query("SELECT * FROM orders WHERE status = 'Delivered' ORDER BY order_date DESC");
        res.json({
            outForDelivery: deliveryRes.rows,
            delivered: deliveredRes.rows
        });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// UPDATE an order's status to 'Delivered'
app.put('/api/orders/:id/deliver', async (req, res) => { /* ... no change ... */ 
    try {
        const { id } = req.params;
        const { rows } = await pool.query("UPDATE orders SET status = 'Delivered' WHERE id = $1 RETURNING *", [id]);
        res.json({ success: true, order: rows[0] });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
    initializeDatabase();
});

