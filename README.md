# Inventory Management System

A desktop-based Inventory Management System built for **Nitya Sales** using **Python**, **Tkinter**, and **MySQL**.  
The goal of this project was to replace the manual Excel / Google Sheets workflow used for stock tracking, reports, and daily business operations with one centralized desktop application.

## Overview

This application manages the complete inventory workflow for a retail business, including:

- product management
- daily stock tracking
- order processing
- billing and invoice generation
- dealer management
- sales/profit reporting
- CSV import and export
- user access control

It is designed as a practical business tool rather than a simple CRUD project.

## Features

### Dashboard
- Sales performance summary
- Current inventory summary
- Total orders count
- Date-wise inventory overview

### Product Management
- Add new products
- View all products in a searchable table
- Filter products by name or brand
- Toggle product status as active/inactive
- Import product data from CSV

### Inventory Management
- Track opening stock, purchase, sales, and balance stock
- View stock records by date
- Filter inventory by brand and product name
- Export inventory data to CSV
- Update opening stock and purchase values directly from the table

### Order Management
- Create new orders for dealers/customers
- Add multiple items to cart
- Validate available stock before adding items
- Edit existing orders
- Automatically sync stock when an order is created, updated, or deleted

### Billing
- Generate invoices for pending orders
- Save invoice number and billing details
- Update order status after billing
- Keep billing and order history synchronized

### Dealer Management
- Store dealer details
- Import dealer data through CSV
- View dealers in a table
- Filter dealers based on FOS field

### Reporting
- Sales and profit reports
- Date range filtering
- Dealer-wise revenue tracking
- Order-item drill-down view

### User Access Control
- View all users
- Edit permissions for selected users
- Role-based access handling

### Utility Features
- CSV import/export support
- Multi-page desktop UI
- MySQL-backed persistent storage
- Date-wise stock carry-forward logic

## Tech Stack

- **Python**
- **Tkinter**
- **MySQL**
- **mysql-connector-python**
- **CSV module**

## Screenshots

Add screenshots of:
1. Dashboard
2. Inventory Stock Status
3. Product Management
4. Order History
5. Billing / Reports
6. User Access Control

For a project card, upload the **Dashboard** screenshot as the main image.

## Database Setup

Create a MySQL database named:

```sql
inventory
```

The application expects tables such as:

- `product`
- `stock`
- `tempo`
- `dealer`
- `orders`
- `order_items`
- `invoices`
- `users`

## How to Run

1. Install the required Python package:
```bash
pip install mysql-connector-python
```

2. Make sure MySQL is running locally.

3. Update the database credentials in the script if needed.

4. Run the application:
```bash
python inventory.py
```

## Notes

- The project currently uses dummy data for presentation and testing.
- The system is built as a desktop application using Tkinter.
- It was developed for **Nitya Sales** to make stock and order handling more structured than spreadsheet-based tracking.

## License

This repository currently does not include a license file.

If you want other people to legally reuse, modify, or distribute the code, add a license file before making the repository public.

If you want the project to remain private or company-specific, you can keep it without a public license and mention:

> All rights reserved. Unauthorized reuse is not permitted.

## Author

Developed by **Popat Mishra** for **Nitya Sales**.
