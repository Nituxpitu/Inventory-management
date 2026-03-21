# -------------------- IMPORTS --------------------
import mysql.connector
import tkinter as kt
from tkinter import filedialog, messagebox, ttk
import csv as c
import datetime
from tkinter import simpledialog
from datetime import date

a=date.today()
mydb = mysql.connector.connect(
        host="localhost",    
        user='root' ,  # NEW LAN USER
        password="mysql",
        database="inventory"
    )

mycursor = mydb.cursor(buffered=True)
current_user = None  # Stores the logged-in user's data
# NEW: Uses the global data built during login
global nav_data


# -------------------- SINGLE CLICK STATUS TOGGLE (✔ / ❌) --------------------

def toggle_status_from_table(event, table):
    row_id = table.identify_row(event.y)
    col_id = table.identify_column(event.x)

    # Trigger ONLY on the Status column (#7)
    if col_id != "#7" or not row_id:
        return

    row = table.item(row_id)["values"]
    product_id = row[0]
    current_symbol = row[6]

    # Decide new status and update the inventory table accordingly
    if current_symbol == "✔":
        new_status = "Deactive"
        new_symbol = "❌"
        # EFFECT IN INVENTORY: Remove the item from today's stock list
        mycursor.execute("DELETE FROM stock WHERE product_id=%s AND s_date=%s", (product_id, a))
    else:
        new_status = "Active"
        new_symbol = "✔"
        # EFFECT IN INVENTORY: Re-add the item to today's stock list if it was missing
        mycursor.execute("""
            INSERT IGNORE INTO stock (product_id, O_stock, purchase, sales, b_stock, s_date) 
            VALUES (%s, 0, 0, 0, 0, %s)
        """, (product_id, a))

    # Update the product's status in the main product table
    mycursor.execute("UPDATE product SET status=%s WHERE product_id=%s", (new_status, product_id))
    mydb.commit()

    # Update the UI Treeview immediately
    new_values = list(row)
    new_values[6] = new_symbol
    table.item(row_id, values=new_values)
def export_to_csv(tree, report_name="Export"):
    # 1. Ask user where to save the file
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        title=f"Save {report_name}"
    )
    
    if not file_path:  # If user cancels
        return

    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = c.writer(file)
            
            # 2. Extract column headers from the Treeview
            headers = [tree.heading(col)['text'] for col in tree['columns']]
            writer.writerow(headers)
            
            # 3. Extract all row data currently in the Treeview
            for row_id in tree.get_children():
                row_data = tree.item(row_id)['values']
                writer.writerow(row_data)
                
        messagebox.showinfo("Export Success", f"Data exported successfully to:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Export Error", f"An error occurred: {e}")
def change_o_stock(event, table):
    row = table.identify_row(event.y) 
    column = table.identify_column(event.x)  # identify_column needs event.x
    
    if not row or column != '#3':
        return

    r = table.item(row)['values']
    product_name = r[1]
    selected_date = r[8] # Get date from row to use in UPDATE

    mycursor.execute(
        "SELECT product_id FROM product WHERE product_name=%s",
        (product_name,)
    )
    result = mycursor.fetchone()
    if not result:
        return
    p_id = result[0] # result is the tuple, result[0] is the ID

    O_stock = simpledialog.askinteger(
        "Update Opening Stock",
        f"Enter new Opening stock for {product_name}:"
    )
    
    if O_stock is None:
        return

    # Update Query: Added a comma between %s and b_stock
    mycursor.execute(
        "UPDATE stock SET O_stock=%s, b_stock=%s WHERE product_id=%s AND s_date=%s",
        (O_stock, O_stock, p_id, selected_date)
    )
    mydb.commit()

    # Refresh table
    table.delete(*table.get_children())
    
    # Try to find date from combobox if available, otherwise use row date
    for widget in table.master.winfo_children():
        if isinstance(widget, ttk.Combobox):
            selected_date = widget.get()
            break

    if selected_date:
        mycursor.execute("""
            SELECT p.brand, p.product_name, s.O_stock, s.purchase, s.sales, s.b_stock, p.p_rate, p.s_rate, s.s_date
            FROM product p
            JOIN stock s ON p.product_id = s.product_id
            WHERE s.s_date = %s
        """, (selected_date,))
    else:
        mycursor.execute("""
            SELECT p.brand, p.product_name, s.O_stock, s.purchase, s.sales, s.b_stock, p.p_rate, p.s_rate, s.s_date
            FROM product p
            JOIN stock s ON p.product_id = s.product_id
        """)

    for row_data in mycursor.fetchall():
        table.insert("", "end", values=row_data)



def purchase_new(event, table):
    row = table.identify_row(event.y)
    column = table.identify_column(event.x)

    # Purchase column is #4 in your stock table
    if not row or column != "#4":
        return

    r = table.item(row)["values"]
    product_name = r[1]
    bal = r[5]
    
    mycursor.execute(
        "SELECT product_id FROM product WHERE product_name=%s",
        (product_name,)
    )
    result = mycursor.fetchone()
    if not result:
        return

    p_id = result[0]

    new_purchase = simpledialog.askinteger(
        "Update Stock",
        f"Enter new purchase for {product_name}:"
    )

    if new_purchase is None:
        return

    new_balance = bal + new_purchase

    mycursor.execute(
        "UPDATE stock SET purchase=%s, b_stock=%s WHERE product_id=%s AND s_date=%s",
        (new_purchase, new_balance, p_id,a)
    )
    mydb.commit()

    # ✅ REFRESH ONLY THE CURRENT TABLE
    table.delete(*table.get_children())

    # Reload data for currently selected date
    selected_date = r[8]
    for widget in table.master.winfo_children():
        if isinstance(widget, ttk.Combobox):
            selected_date = widget.get()
            break

    if selected_date:
        mycursor.execute("""
            SELECT  p.brand, p.product_name,s.O_stock, s.purchase,s.sales, s.b_stock, p.p_rate,p.s_rate, s.s_date
                FROM product p
                JOIN stock s ON p.product_id = s.product_id
                WHERE s.s_date = %s
        """, (selected_date,))
    else:
        mycursor.execute("""
             SELECT  p.brand, p.product_name,s.O_stock, s.purchase,s.sales, s.b_stock, p.p_rate,p.s_rate, s.s_date
                FROM product p
                JOIN stock s ON p.product_id = s.product_id
            
        """)

    for row in mycursor.fetchall():
        table.insert("", "end", values=row)

    

# -------------------- MAIN WINDOW --------------------
window = kt.Tk()
window.geometry("420x420")
window.title("Inventory Manager")
window.config(background="cyan")
container=kt.Frame(window)

container.pack(fill="both", expand=True)
container.grid_rowconfigure(0, weight=1)
container.grid_columnconfigure(0, weight=1)

search_frame = kt.Frame(container)
product_frame=kt.Frame(search_frame)

dash_frame=kt.Frame(container)


order_page=kt.Frame(container)
order_frame=kt.Frame(order_page)
cust_more=kt.Frame(container)
for f in (dash_frame,order_page ,cust_more,order_frame,search_frame,product_frame):
    f.grid(row=0, column=0, sticky="nsew")



# -------------------- VIEW TABLE --------------------
def view_table():
    for widget in search_frame.winfo_children():
        widget.destroy()
    
    # Theme Colors
    bg_main = "#f0f4f8"       # Light blue-grey background
    sidebar_color = "#1a365d" # Dark navy blue
    card_color = "#ffffff"    # White card background
    accent_blue = "#2b6cb0"   # Medium blue
    text_dark = "#2d3748"     # Dark grey

    search_frame.config(bg=bg_main)
    show_page(search_frame)

    # 1. Sidebar Navigation (Consistent with Dashboard)
    sidebar = kt.Frame(search_frame, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")

    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()

    # Inside your order_page_frame() and other page functions:
    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]

    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, activebackground=accent_blue, 
                  activeforeground="white", anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. Main Content Area
    content = kt.Frame(search_frame, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    # Header Row
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))

    kt.Label(header_row, text="Product Management", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(side="left")

    kt.Button(header_row, text="+ Add New Product", font=("Arial", 11, "bold"), 
              bg="#38a169", fg="white", padx=15, pady=8, bd=0,
              command=pro_frame).pack(side="right")

    # 3. Search Bar Card
    search_card = kt.Frame(content, bg=card_color, padx=15, pady=15, 
                           highlightbackground="#cbd5e0", highlightthickness=1)
    search_card.pack(fill="x", pady=(0, 20))

    kt.Label(search_card, text="Search:", font=("Arial", 10, "bold"), bg=card_color).pack(side="left")
    search_entry = kt.Entry(search_card, width=25, font=("Arial", 10))
    search_entry.pack(side="left", padx=10)

    kt.Label(search_card, text="Filter By:", font=("Arial", 10, "bold"), bg=card_color).pack(side="left")
    search_type = ttk.Combobox(search_card, values=["product_name", "brand"], state="readonly", width=15)
    search_type.set("product_name")
    search_type.pack(side="left", padx=10)

    kt.Button(search_card, text="🔍 Search", bg=accent_blue, fg="white", bd=0, 
              padx=15, command=lambda: search()).pack(side="left", padx=5)

    # 4. Product Table Card
    table_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True)

    table = ttk.Treeview(
        table_card, 
        columns=("id","name","brand","cat","pr","sr","status"),
        show='headings'
    )

    headings = ["ID","Product Name","Brand","Category","P Rate","S Rate","Status"]
    for col, head in zip(table["columns"], headings):
        table.heading(col, text=head.upper())
        table.column(col, anchor="center", width=110)

    table.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    
    # Logic to load data and bind click
    def load_data(query=None, value=None):
        for row in table.get_children(): table.delete(row)
        if query is None: mycursor.execute("SELECT * FROM product")
        else: mycursor.execute(query, (value,))
        
        for row in mycursor.fetchall():
            sym = "✔" if row[6] == "Active" else "❌"
            table.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], row[5], sym))

    def search():
        col = search_type.get()
        txt = search_entry.get()
        if not txt: load_data()
        else: load_data(f"SELECT * FROM product WHERE {col} LIKE %s", f"%{txt}%")

    table.bind("<Button-1>", lambda event: toggle_status_from_table(event, table))
    load_data()


# -------------------- CSV UPLOAD --------------------
def upload():
    file_path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv")]
    )

    if not file_path:
        return

    query = """
    INSERT INTO tempo
    (product_name, brand, catagory, p_rate, s_rate,o_stock,purchase,sales,b_stock, status,s_date)
    VALUES  ( %s, %s, %s, %s, %s, %s, %s, %s, %s,'Active',%s)
    """

    with open(file_path, 'r') as csvfile:
        reader = c.DictReader(csvfile)
        for row in reader:
            values = (
                row['product_name'],
                row['brand'],
                row['category'],
                row['prate'],
                row['srate'],
                row['o_stock'],
                row['purchase'],
                row['sales'],
                row['b_stock'],
                a
                
            )
            mycursor.execute(query, values)

    mydb.commit()
    mycursor.execute("INSERT INTO product (product_name, brand, catagory, p_rate, s_rate, Status) select distinct product_name, brand, catagory, p_rate, s_rate, status FROM tempo WHERE product_name NOT IN (SELECT product_name FROM product)")
    
    mycursor.execute("INSERT INTO stock (product_id, O_stock, purchase, sales, b_stock,s_date) select p.product_id, t.O_stock, t.purchase, t.sales, t.b_stock, t.s_date FROM tempo t JOIN product p ON t.product_name = p.product_name")
    mydb.commit()
   
    mycursor.execute("TRUNCATE TABLE tempo")
    messagebox.showinfo("Success", "CSV Imported Successfully!")
def change_data():
    try:
        # 1. Get the current date from the system
        today = datetime.date.today()

        # 2. Check if today's records already exist
        mycursor.execute("SELECT COUNT(*) FROM stock WHERE s_date = %s", (today,))
        if mycursor.fetchone()[0] > 0:
            print(f"Records for {today} already exist.")
            return

        # 3. Find the most recent date in the database
        mycursor.execute("SELECT MAX(s_date) FROM stock")
        last_recorded_date = mycursor.fetchone()[0]

        if last_recorded_date:
            # 4. Carry forward the 'b_stock' (Balance) from the last date 
            # to the 'o_stock' (Opening) of today.
            query = """
                INSERT INTO stock (product_id, o_stock, purchase, sales, b_stock, s_date) 
                SELECT product_id, b_stock, 0, 0, b_stock, %s 
                FROM stock 
                WHERE s_date = %s
            """
            mycursor.execute(query, (today, last_recorded_date))
            mydb.commit()
            print(f"Successfully carried stock forward from {last_recorded_date} to {today}")
        else:
            print("No previous records found to carry forward.")

    except Exception as e:
        print(f"Error updating daily stock: {e}")
def view_table_stock():
    # 1. Clear the frame to prepare for the new UI
    for widget in dash_frame.winfo_children():
        widget.destroy()
    
    # --- THEME COLORS ---
    bg_main = "#f0f4f8"       # Light blue-grey background
    sidebar_color = "#1a365d" # Dark navy blue
    card_color = "#ffffff"    # White card background
    accent_blue = "#2b6cb0"   # Medium blue
    text_dark = "#2d3748"     # Dark grey

    dash_frame.config(bg=bg_main)
    show_page(dash_frame)

    # 1. SIDEBAR NAVIGATION (Consistent with Dashboard)
    sidebar = kt.Frame(dash_frame, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")

    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()
    # Locate your filter_card button section and add this:
    
    # Inside your order_page_frame() and other page functions:
    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, activebackground=accent_blue, 
                  activeforeground="white", anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(dash_frame, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    # Header Row
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))

    kt.Label(header_row, text="Inventory Stock Status", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(side="left")

    # 3. FILTER CARD (Search Controls)
    filter_card = kt.Frame(content, bg=card_color, padx=15, pady=15, 
                           highlightbackground="#cbd5e0", highlightthickness=1)
    filter_card.pack(fill="x", pady=(0, 20))

    # Date Filter
    kt.Label(filter_card, text="Date:", font=("Arial", 10, "bold"), bg=card_color).pack(side="left", padx=(0, 5))
    date_filter = ttk.Combobox(filter_card, state="readonly", width=12)
    date_filter.pack(side="left", padx=5)

    # Brand Filter
    kt.Label(filter_card, text="Brand:", font=("Arial", 10, "bold"), bg=card_color).pack(side="left", padx=(10, 5))
    brand_filter = ttk.Combobox(filter_card, values=["All", "hp", "oppo", "earthonic"], state="readonly", width=10)
    brand_filter.set("All")
    brand_filter.pack(side="left", padx=5)

    # Model Search
    kt.Label(filter_card, text="Model:", font=("Arial", 10, "bold"), bg=card_color).pack(side="left", padx=(10, 5))
    name_search = kt.Entry(filter_card, width=20)
    name_search.pack(side="left", padx=5)

    # Search Button
    
    kt.Button(filter_card, text="🔍 Search", bg=accent_blue, fg="white", font=("Arial", 10, "bold"),
              padx=15, bd=0, command=lambda: load_filtered_data()).pack(side="left", padx=15)

    # 4. TABLE CARD (Inventory Treeview)
    table_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True)

    columns = ("brand", "product_name", "o_stock", "purchase", "sales", "b_stock", "p_rate", "s_rate", "s_date")
    tree = ttk.Treeview(table_card, columns=columns, show="headings")
    
    # Column Setup
    tree.heading("brand", text='BRAND')
    tree.column('brand', width=100, anchor='center')
    tree.heading('product_name', text='MODEL')
    tree.column('product_name', width=240, anchor='center')
    
    for i in range(2, 9):
        tree.heading(columns[i], text=columns[i].replace('_', ' ').upper())
        tree.column(columns[i], width=100, anchor="center")
    
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    kt.Button(filter_card, 
              text="📥 Export CSV", 
              bg="#38a169", # Green color for export
              fg="white", 
              command=lambda: export_to_csv(tree, "Inventory_Report"), 
              padx=15).pack(side="left", padx=10)
    # --- DYNAMIC FILTER LOGIC ---
    def load_filtered_data(event=None):
        for item in tree.get_children():
            tree.delete(item)
            
        selected_date = date_filter.get()
        selected_brand = brand_filter.get()
        search_text = name_search.get().strip()
        
        try:
            query = """
                SELECT p.brand, p.product_name, s.O_stock, s.purchase, s.sales, s.b_stock, p.p_rate, p.s_rate, s.s_date
                FROM product p
                JOIN stock s ON p.product_id = s.product_id
                WHERE s.s_date = %s
            """
            params = [selected_date]

            if selected_brand != "All":
                query += " AND p.brand = %s"
                params.append(selected_brand)

            if search_text:
                query += " AND p.product_name LIKE %s"
                params.append(f"%{search_text}%")

            mycursor.execute(query, tuple(params))
            for row in mycursor.fetchall():
                tree.insert("", "end", values=row)
        except Exception as e:
            print(f"Error filtering data: {e}")

    # --- POPULATE INITIAL DATA ---
    try:
        mycursor.execute("SELECT DISTINCT s_date FROM stock ORDER BY s_date DESC")
        available_dates = [str(date[0]) for date in mycursor.fetchall()]
        if available_dates:
            date_filter['values'] = available_dates
            date_filter.set(available_dates[0])
            load_filtered_data()
    except Exception as e:
        print(f"Error fetching dates: {e}")

    # Bindings for interactive search
    tree.bind("<Double-1>", lambda revent: change_o_stock(revent, tree))
    tree.bind("<Button-1>", lambda revent: purchase_new(revent, tree))
    date_filter.bind("<<ComboboxSelected>>", load_filtered_data)
    brand_filter.bind("<<ComboboxSelected>>", load_filtered_data)
    name_search.bind("<Return>", lambda e: load_filtered_data())

def build_dashboard(target_date=None):
    # Clear dashboard if rebuilt accidentally
    for widget in dash_frame.winfo_children():
        widget.destroy()

    # Define dynamic target date (defaults to current system date 'a')
    view_date = target_date if target_date else str(a)

    # --- MODERN THEME COLORS ---
    bg_main = "#f0f4f8"
    sidebar_color = "#1a365d"
    card_color = "#ffffff"
    accent_blue = "#2b6cb0"
    text_dark = "#2d3748"

    dash_frame.config(bg=bg_main)

    # 1. SIDEBAR
    sidebar = kt.Frame(dash_frame, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")

    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 18, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()

    # Inside your order_page_frame() and other page functions:
    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, activebackground=accent_blue, 
                  activeforeground="white", anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(dash_frame, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    # Header Row
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 25))

    kt.Label(header_row, text="Inventory Overview", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(side="left")

    # Date Filter
    date_filter = ttk.Combobox(header_row, state="readonly", width=15)
    date_filter.pack(side="right", padx=10)
    
    kt.Label(header_row, text="Filter Date:", font=("Arial", 10), 
             bg=bg_main, fg=text_dark).pack(side="right")

    mycursor.execute("SELECT DISTINCT s_date FROM stock ORDER BY s_date DESC")
    available_dates = [str(d[0]) for d in mycursor.fetchall()]
    date_filter['values'] = available_dates
    date_filter.set(view_date)

    def on_date_change(event):
        build_dashboard(target_date=date_filter.get())

    date_filter.bind("<<ComboboxSelected>>", on_date_change)

    # --- DATABASE CALCULATIONS ---

    # 1. Total Units Sold
    mycursor.execute("SELECT SUM(sales) FROM stock WHERE s_date = %s", (view_date,))
    sold_qty = mycursor.fetchone()[0] or 0

    # 2. Total Sales Value
    mycursor.execute("""
        SELECT SUM(s.sales * p.s_rate) 
        FROM stock s JOIN product p ON s.product_id = p.product_id 
        WHERE s.s_date = %s
    """, (view_date,))
    sales_val = mycursor.fetchone()[0] or 0

    # 3. Total Available Stock
    mycursor.execute("SELECT SUM(b_stock) FROM stock WHERE s_date = %s", (view_date,))
    stock_qty = mycursor.fetchone()[0] or 0

    # 4. Total Stock Value
    mycursor.execute("""
        SELECT SUM(s.b_stock * p.p_rate) 
        FROM stock s JOIN product p ON s.product_id = p.product_id 
        WHERE s.s_date = %s
    """, (view_date,))
    stock_val = mycursor.fetchone()[0] or 0

    # 5. 🔥 TOTAL NUMBER OF ORDERS FOR SELECTED DATE (NEW)
    mycursor.execute("SELECT COUNT(*) FROM orders WHERE order_date = %s", (view_date,))
    total_orders = mycursor.fetchone()[0] or 0

    # --- STATISTICS CARDS DISPLAY ---
    cards_frame = kt.Frame(content, bg=bg_main)
    cards_frame.pack(fill="x")

    # Sales Performance Card
    c1 = kt.Frame(cards_frame, bg=card_color, highlightbackground="#cbd5e0",
                  highlightthickness=1, padx=20, pady=20)
    c1.pack(side="left", expand=True, fill="both", padx=(0, 10))
    kt.Label(c1, text="SALES PERFORMANCE", font=("Arial", 9, "bold"),
             bg=card_color, fg="#718096").pack(anchor="w")
    kt.Label(c1, text=f"{sold_qty} Items Sold", font=("Arial", 16, "bold"),
             bg=card_color, fg=accent_blue).pack(anchor="w", pady=5)
    kt.Label(c1, text=f"Value: ₹{sales_val:,.2f}", font=("Arial", 11),
             bg=card_color, fg=text_dark).pack(anchor="w")

    # Current Inventory Card
    c2 = kt.Frame(cards_frame, bg=card_color, highlightbackground="#cbd5e0",
                  highlightthickness=1, padx=20, pady=20)
    c2.pack(side="left", expand=True, fill="both", padx=(10, 10))
    kt.Label(c2, text="CURRENT INVENTORY", font=("Arial", 9, "bold"),
             bg=card_color, fg="#718096").pack(anchor="w")
    kt.Label(c2, text=f"{stock_qty} Units in Stock", font=("Arial", 16, "bold"),
             bg=card_color, fg=accent_blue).pack(anchor="w", pady=5)
    kt.Label(c2, text=f"Value: ₹{stock_val:,.2f}", font=("Arial", 11),
             bg=card_color, fg=text_dark).pack(anchor="w")

    # 🔥 TOTAL ORDERS CARD (NEW)
    c3 = kt.Frame(cards_frame, bg=card_color, highlightbackground="#cbd5e0",
                  highlightthickness=1, padx=20, pady=20)
    c3.pack(side="left", expand=True, fill="both", padx=(10, 0))
    kt.Label(c3, text="TOTAL ORDERS", font=("Arial", 9, "bold"),
             bg=card_color, fg="#718096").pack(anchor="w")
    kt.Label(c3, text=f"{total_orders} Orders", font=("Arial", 16, "bold"),
             bg=card_color, fg=accent_blue).pack(anchor="w", pady=5)
    kt.Label(c3, text=f"Date: {view_date}", font=("Arial", 11),
             bg=card_color, fg=text_dark).pack(anchor="w")

    # 3. SYSTEM LOG PANEL
    log_panel = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0",
                         highlightthickness=1, pady=15, padx=15)
    log_panel.pack(fill="both", expand=True, pady=25)

    kt.Label(log_panel, text="System Log", font=("Arial", 12, "bold"),
             bg=card_color, fg=text_dark).pack(anchor="w")
    kt.Label(log_panel, text=f"• Records currently shown for date: {view_date}", 
             font=("Arial", 10), bg=card_color, fg=text_dark).pack(anchor="w", pady=5)
def pro_frame():
    global product_frame
    
    # 1. Validation: If the frame doesn't exist or was destroyed, recreate it as a child of 'container'
    if not product_frame.winfo_exists():
        product_frame = kt.Frame(container)
        product_frame.grid(row=0, column=0, sticky="nsew")

    # 2. Safely clear internal contents
    try:
        for widget in product_frame.winfo_children():
            widget.destroy()
    except kt.TclError:
        # If a race condition occurs, recreate the frame entirely
        product_frame = kt.Frame(container)
        product_frame.grid(row=0, column=0, sticky="nsew")
    
    # --- THEME COLORS ---
    bg_main = "#f0f4f8"       
    sidebar_color = "#1a365d" 
    card_color = "#ffffff"    
    accent_blue = "#2b6cb0"   
    text_dark = "#2d3748"     

    product_frame.config(bg=bg_main)
    show_page(product_frame)

    # 1. SIDEBAR NAVIGATION
    sidebar = kt.Frame(product_frame, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")

    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()

    # Inside your order_page_frame() and other page functions:
    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]

    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, activebackground=accent_blue, 
                  activeforeground="white", anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(product_frame, bg=bg_main, padx=40, pady=30)
    content.pack(side="right", fill="both", expand=True)

    # Header
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))

    kt.Label(header_row, text="Add New Product", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(side="left")

    # 3. PRODUCT FORM CARD
    form_card = kt.Frame(content, bg=card_color, padx=30, pady=30, 
                         highlightbackground="#cbd5e0", highlightthickness=1)
    form_card.pack(fill="both", expand=True)

    # Helper function to create labeled entries
    def create_field(parent, label_text, row):
        kt.Label(parent, text=label_text, font=("Arial", 10, "bold"), bg=card_color, fg=text_dark).grid(row=row, column=0, sticky="w", pady=(10, 2))
        entry = kt.Entry(parent, font=("Arial", 11), width=40, bd=1, relief="solid")
        entry.grid(row=row+1, column=0, sticky="w", pady=(0, 10))
        return entry

    def create_combo(parent, label_text, values, row):
        kt.Label(parent, text=label_text, font=("Arial", 10, "bold"), bg=card_color, fg=text_dark).grid(row=row, column=0, sticky="w", pady=(10, 2))
        combo = ttk.Combobox(parent, values=values, font=("Arial", 11), width=37, state="readonly")
        combo.grid(row=row+1, column=0, sticky="w", pady=(0, 10))
        return combo

    # Form Fields
    entry_name = create_field(form_card, "Product Name", 0)
    combo_brand = create_combo(form_card, "Brand", ["hp", "oppo", "earthonic"], 2)
    combo_cat = create_combo(form_card, "Category", ["laptop", "mobile", "TV"], 4)
    entry_prate = create_field(form_card, "Purchase Rate (PRate)", 6)
    entry_srate = create_field(form_card, "Sales Rate (SRates)", 8)
    entry_ostock = create_field(form_card, "Opening Stock", 10)
    entry_bstock = create_field(form_card, "Balance Stock", 12)

    # 4. ACTION BUTTONS
    btn_frame = kt.Frame(form_card, bg=card_color)
    btn_frame.grid(row=14, column=0, sticky="w", pady=20)

    def store_data():   
        try:
            query = """
            INSERT INTO tempo
            (product_name, brand, catagory, p_rate, s_rate, o_stock, purchase, sales, b_stock, status, s_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s)
            """
            values = (
                entry_name.get(), combo_brand.get(), combo_cat.get(),
                entry_prate.get(), entry_srate.get(), entry_ostock.get(),
                0, 0, entry_bstock.get(), a
            )

            mycursor.execute(query, values)
            mydb.commit()
            
            p_id = mycursor.lastrowid
            mycursor.execute("INSERT INTO product (product_name, brand, catagory, p_rate, s_rate, Status) SELECT DISTINCT product_name, brand, catagory, p_rate, s_rate, status FROM tempo WHERE product_name NOT IN (SELECT product_name FROM product)")
            mycursor.execute("INSERT INTO stock (product_id, O_stock, purchase, sales, b_stock, s_date) SELECT p.product_id, t.O_stock, t.purchase, t.sales, t.b_stock, t.s_date FROM tempo t JOIN product p ON t.product_name = p.product_name")
            mydb.commit()
            mycursor.execute("TRUNCATE TABLE tempo")

            messagebox.showinfo("Success", f"Product Stored Successfully\nID: {p_id}")
            view_table() 
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    kt.Button(btn_frame, text="💾 Save Product", font=("Arial", 11, "bold"), bg="#38a169", fg="white", padx=20, pady=8, bd=0, command=store_data).pack(side="left", padx=(0, 15))
    kt.Button(btn_frame, text="📥 Import CSV", font=("Arial", 11), bg=accent_blue, fg="white", padx=20, pady=8, bd=0, command=upload).pack(side="left")
def open_order_frame(view_id=None):
    global order_frame
    # 1. Initialize Frame
    if not order_frame.winfo_exists():
        order_frame = kt.Frame(order_page)
        order_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    for widget in order_frame.winfo_children():
        widget.destroy()

    # UI Theme
    bg_color, accent_green, accent_blue = "#f4f4f4", "#2dcf58", "#2b6cb0"
    order_frame.config(bg=bg_color)
    show_page(order_frame)

    # State tracking
    editing_order_id = view_id

    # --- 2. LOGIC FUNCTIONS (Defined first to avoid scope errors) ---

    def update_running_total():
        total_sum = 0
        for item in cart_table.get_children():
            try:
                total_sum += float(cart_table.item(item)['values'][4])
            except: continue
        running_total_var.set(f"Running Total: ₹ {total_sum:,.2f}")

    def update_products(event):
        selected_brand = brand_cb.get()
        query = "SELECT p.product_name FROM product p JOIN stock s ON p.product_id = s.product_id WHERE s.b_stock > 0 AND s.s_date = %s"
        params = [a]
        if selected_brand != "All":
            query = "SELECT p.product_name FROM product p JOIN stock s ON p.product_id = s.product_id WHERE p.brand = %s AND s.b_stock > 0 AND s.s_date = %s"
            params = [selected_brand, a]
        
        mycursor.execute(query, tuple(params))
        prod_cb['values'] = [j[0] for j in mycursor.fetchall()]
        prod_cb.set('')

    def fetch_details(event):
        p_name = prod_cb.get()
        mycursor.execute("SELECT product_id, s_rate FROM product WHERE product_name=%s", (p_name,))
        res = mycursor.fetchone()
        if res:
            p_id, s_rate = res
            selling_rate_var.set(s_rate)
            mycursor.execute("SELECT b_stock FROM stock WHERE product_id=%s AND s_date=%s", (p_id, d_ate.get()))
            stock_res = mycursor.fetchone()
            m = stock_res[0] if stock_res else 0
            stok_lbl.config(text=f"Available Stock: {m}", fg="green" if m > 0 else "red")

    def add_to_cart():
        p_name, rate, qty = prod_cb.get(), selling_rate_var.get(), qty_entry.get()
        mycursor.execute("Select product_id from product where product_name=%s",(p_name,))
        p_id=mycursor.fetchone()[0]
        mycursor.execute("SELECT b_stock FROM stock WHERE product_id=%s AND s_date=%s", (p_id, d_ate.get()))
        stock_res = mycursor.fetchone()[0]
        if not p_name or not qty.isdigit() or int(qty)>int(stock_res):
            messagebox.showerror("Error", "Invalid entry.")
            return
       
        
        mycursor.execute("SELECT product_id FROM product WHERE product_name=%s", (p_name,))
        p_id = mycursor.fetchone()[0]
        item_total = float(rate) * int(qty)
        cart_table.insert("", "end", values=(p_id, p_name, rate, qty, item_total))
        update_running_total()
        qty_entry.delete(0, kt.END)

    def remove_selected():
        for item in cart_table.selection():
            cart_table.delete(item)
        update_running_total()
    def search(event):
        typed = dealer_cb.get().lower()

        if typed == "":
            dealer_cb["values"] = dealer_list
            return

        filtered = [d for d in dealer_list if typed in d.lower()]
        dealer_cb["values"] = filtered

    def on_select(event):
        dealer_cb.set(dealer_cb.get())
   
    # DO NOT force <Down> here
    def proceed_to_billing():
        dealer_name = dealer_cb.get()
        items = cart_table.get_children()
        dte=d_ate.get()
        if dealer_name == "Select Dealer" or not items:
            messagebox.showerror("Error", "Check inputs.")
            return

        try:
            # 1. Get Dealer ID
            mycursor.execute("SELECT d_id FROM dealer WHERE d_name=%s", (dealer_name,))
            d_id = mycursor.fetchone()[0]
            
            # 2. Create the Parent Order
            mycursor.execute("INSERT INTO orders (d_id, order_date, status) VALUES (%s, %s, 'Pending')", (d_id, dte))
            new_id = mycursor.lastrowid
            
            # 3. Loop through EVERY item in the cart table
            for item in items:
                v = cart_table.item(item)['values']
                p_id = v[0]  # Product ID
                qty = v[3]   # Quantity purchased
                t_price = v[4]

                # INSERT into order_items
                mycursor.execute("INSERT INTO order_items (order_id, product_id, QTY, t_price) VALUES (%s, %s, %s, %s)", 
                                (new_id, p_id, qty, t_price))
                
                # UPDATE stock for THIS specific product
                mycursor.execute("UPDATE stock SET sales = sales + %s, b_stock = b_stock - %s WHERE product_id = %s and s_date=%s",
                                (qty, qty, p_id,dte))

            mydb.commit()
            messagebox.showinfo("Success", f"Order {new_id} Saved and Stock Updated")
            order_page_frame()

        except Exception as e:
            mydb.rollback()
            messagebox.showerror("Error", str(e))
    def filter_dealers_by_fos(event=None):
        selected_fos = FOS_cb.get()

        if selected_fos == "":
            dealer_cb["values"] = []
            dealer_cb.set("")
            return

        mycursor.execute(
            "SELECT d_name FROM dealer WHERE FOS=%s",
            (selected_fos,)
        )
        dealer_list = [row[0] for row in mycursor.fetchall()]

        dealer_cb["values"] = dealer_list
        dealer_cb.set("")

    def update_existing_order():
        dte=d_ate.get()
        if not editing_order_id: 
            return
            
        try:
            # STEP 1: Undo the old stock changes
            # Get all items currently attached to this order before we delete them
            mycursor.execute("SELECT product_id, QTY FROM order_items WHERE order_id=%s", (editing_order_id,))
            old_items = mycursor.fetchall()
            
            for p_id, old_qty in old_items:
                # Revert: add back to stock, remove from sales
                mycursor.execute("""
                    UPDATE stock 
                    SET b_stock = b_stock + %s, sales = sales - %s 
                    WHERE product_id = %s and s_date=%s
                """, (old_qty, old_qty, p_id,dte))

            # STEP 2: Delete old order items
            mycursor.execute("DELETE FROM order_items WHERE order_id=%s", (editing_order_id,))

            # STEP 3: Insert new items and apply new stock reduction
            for item in cart_table.get_children():
                v = cart_table.item(item)['values']
                new_p_id = v[0]
                new_qty = v[3]
                t_price = v[4]

                # Insert new record
                mycursor.execute("""
                    INSERT INTO order_items (order_id, product_id, QTY, t_price) 
                    VALUES (%s, %s, %s, %s)
                """, (editing_order_id, new_p_id, new_qty, t_price))
                
                # Apply new stock deduction
                mycursor.execute("""
                    UPDATE stock 
                    SET sales = sales + %s, b_stock = b_stock - %s 
                    WHERE product_id = %s and s_date=%s
                """, (new_qty, new_qty, new_p_id,dte))

            mydb.commit()
            messagebox.showinfo("Updated", f"Order #{editing_order_id} and Stock levels updated!")
            order_page_frame()

        except Exception as e:
            mydb.rollback()
            messagebox.showerror("Error", f"Update failed: {str(e)}")

    # --- 3. UI CONSTRUCTION ---
    top_panel = kt.Frame(order_frame, bg=bg_color, pady=10, padx=20)
    top_panel.pack(fill="x")
    kt.Button(top_panel, text="← Back to Orders", command=order_page_frame).pack(side="left")
    kt.Label(top_panel, text=f"Order Edit Mode: #{editing_order_id}" if editing_order_id else "New Order", font=("Arial", 16, "bold"), bg=bg_color).pack(side="right")

    form_frame = kt.Frame(order_frame, bg=bg_color, padx=20)
    form_frame.pack(fill="x")

    # Dealer / Brand Row
    kt.Label(form_frame, text="Company Filter:", font=("Arial", 14), bg=bg_color)\
        .grid(row=0, column=0, sticky="w", pady=5)
    brand_cb = ttk.Combobox(form_frame, values=["All", "Oppo", "Earthonic", "HP"], state="readonly", width=25)
    brand_cb.grid(row=0, column=1, padx=10); brand_cb.set("All")
    kt.Label(form_frame, text="Party/Dealer Name:", font=("Arial", 14), bg=bg_color)\
        .grid(row=0, column=2, padx=10)
    dealer_cb = ttk.Combobox(form_frame, width=75)
    dealer_cb.grid(row=0, column=3, padx=10)
    mycursor.execute("SELECT d_name FROM dealer")
    dealer_list = [row[0] for row in mycursor.fetchall()]
    dealer_cb["values"] = dealer_list
    dealer_cb.set("")
    kt.Label(form_frame, text='FOS:', font=("Arial", 14), bg=bg_color)\
        .grid(row=0, column=4, sticky='w')

    kt.Label(form_frame, text='FOS:', font=("Arial", 14), bg=bg_color)\
    .grid(row=0, column=4, sticky='w')

    FOS_cb = ttk.Combobox(form_frame, width=10, state="readonly")
    FOS_cb.grid(row=0, column=5, pady=5, sticky='w')

    mycursor.execute("SELECT DISTINCT FOS FROM dealer")
    FOS_list = [row[0] for row in mycursor.fetchall()]
    FOS_cb["values"] = FOS_list
    FOS_cb.set("")


    FOS_cb.bind("<KeyRelease>", search)
    FOS_cb.bind("<<ComboboxSelected>>", filter_dealers_by_fos)

    dealer_cb.bind("<KeyRelease>", search)
    dealer_cb.bind("<<ComboboxSelected>>", on_select)

    # Product / Stock Row

    prod_cb = ttk.Combobox(form_frame, width=70)
    prod_cb.grid(row=1, column=1, padx=10)
    stok_lbl = kt.Label(form_frame, text="Available Stock: -", font=("Arial", 14, "bold"), bg=bg_color)
    stok_lbl.grid(row=1, column=2, columnspan=2, sticky="w", padx=10)
    prod_cb.bind("<KeyRelease>",search)
    # Rate / Qty Row
    mycursor.execute("SELECT DISTINCT s_date FROM stock ORDER BY s_date DESC")
    date_values = [str(date[0]) for date in mycursor.fetchall()]
    kt.Label(form_frame, text="Date:", font=("Arial", 14), bg=bg_color)\
        .grid(row=2, column=1, sticky="e")
    d_ate=ttk.Combobox(form_frame, width=20, state="readonly")
    d_ate.grid(row=2, column=2, padx=10, sticky="w")
    d_ate['values']=date_values
    d_ate.set(a)
    kt.Label(form_frame, text="Quantity:", font=("Arial", 14), bg=bg_color)\
        .grid(row=2, column=2, sticky="e")
    selling_rate_var = kt.StringVar()
    selling_rate_var = kt.StringVar()
    kt.Label(form_frame, text="Selling Rate (₹):", font=("Arial", 14), bg=bg_color)\
        .grid(row=2, column=0, sticky="w", pady=10)
    kt.Entry(form_frame, textvariable=selling_rate_var, font=("Arial", 12), width=27).grid(row=2, column=1, padx=10)
    qty_entry = kt.Entry(form_frame, font=("Arial", 12), width=20)
    qty_entry.grid(row=2, column=3, padx=10, sticky="w")
    kt.Button(form_frame, text="+ Add to Cart", bg=accent_green, fg="white", font=("Arial", 12, "bold"), command=add_to_cart).grid(row=2, column=4, padx=20)
    kt.Label(form_frame, text="Product Name:", font=("Arial", 14), bg=bg_color)\
        .grid(row=1, column=0, sticky="w", pady=5)
    # Cart Table
    columns = ("id", "name", "rate", "qty", "total")
    cart_table = ttk.Treeview(order_frame, columns=columns, show="headings", height=10)
    for col in columns:
        cart_table.heading(col, text=col.upper()); cart_table.column(col, anchor="center")
    cart_table.pack(fill="both", expand=True, padx=20, pady=5)

    # Footer
    footer_frame = kt.Frame(order_frame, bg=bg_color, padx=20, pady=10)
    footer_frame.pack(fill="x")
    running_total_var = kt.StringVar(value="Running Total: ₹ 0")
    kt.Label(footer_frame, textvariable=running_total_var, font=("Arial", 16, "bold"), bg=bg_color).pack(side="right")
    kt.Button(footer_frame, text="✘ Remove Selected", bg="#d9534f", fg="white",
              font=("Arial", 10, "bold"), command=remove_selected).pack(side="left")
    # Dynamic Button assignment
    btn_text = "💾 Update Changes" if editing_order_id else "🛒 Create Order"
    btn_cmd = update_existing_order if editing_order_id else proceed_to_billing
    btn_color = accent_blue if editing_order_id else "#38a169"
    
    billing_btn = kt.Button(footer_frame, text=btn_text, bg=btn_color, fg="white", 
                            font=("Arial", 14, "bold"), command=btn_cmd, padx=25, pady=10)
    billing_btn.pack(side="right", padx=20)

    # --- 4. LOAD DATA IF IN VIEW MODE ---
    if editing_order_id:
        # Load Dealer
        mycursor.execute("SELECT d.d_name FROM orders o JOIN dealer d ON o.d_id = d.d_id WHERE o.order_id = %s", (editing_order_id,))
        res_d = mycursor.fetchone()
        if res_d: dealer_cb.set(res_d[0])

        # Load confirmed items
        mycursor.execute("""
            SELECT oi.product_id, p.product_name, (oi.t_price/oi.QTY), oi.QTY, oi.t_price 
            FROM order_items oi JOIN product p ON oi.product_id = p.product_id WHERE oi.order_id = %s
        """, (editing_order_id,))
        for row in mycursor.fetchall():
            cart_table.insert("", "end", values=row)
        
        update_running_total()

    # Binds
    brand_cb.bind("<<ComboboxSelected>>", update_products)
    prod_cb.bind("<<ComboboxSelected>>", fetch_details)


def order_page_frame():
    for widget in order_page.winfo_children():
        widget.destroy()
    
    # --- THEME COLORS ---
    bg_main, sidebar_color, card_color = "#f0f4f8", "#1a365d", "#ffffff"
    accent_blue, text_dark = "#2b6cb0", "#2d3748"

    order_page.config(bg=bg_main)
    show_page(order_page)

    # 1. SIDEBAR
    sidebar = kt.Frame(order_page, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")
    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"),
             bg=sidebar_color, fg="white", pady=25).pack()

    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color,
                  fg="white", bd=0, anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(order_page, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)
    
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))

    kt.Label(header_row, text="Order History", font=("Arial", 22, "bold"),
             bg=bg_main, fg=text_dark).pack(side="left")

    # --- ACTION BUTTONS ---
    def delete():
        selected=tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select an order to delete.")
            return
        order_id = tree.item(selected[0])['values'][0]
        mycursor.execute("select product_id,qty from order_items where order_id=%s",(order_id,))
        l=mycursor.fetchall()
        for i in l:
            mycursor.execute("update stock set b_stock=b_stock+%s where product_id=%s",(i[1],i[0]))
            mycursor.execute("update stock set sales=sales-%s where product_id=%s",(i[1],i[0]))
            
        mycursor.execute('delete from orders where order_id=%s',(order_id,))
        mydb.commit()
        messagebox.showwarning("Selection", "The order is successfully deleted.")
    def view_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select an order to view.")
            return
        order_id = tree.item(selected[0])['values'][0]
        open_order_frame(view_id=order_id)

    kt.Button(header_row, text="+ New Order", font=("Arial", 12, "bold"),
              bg="#38a169", fg="white", padx=15, pady=8,
              bd=0, command=open_order_frame).pack(side="right")
    
    kt.Button(header_row, text="👁 View Details", font=("Arial", 12, "bold"),
              bg=accent_blue, fg="white", padx=15, pady=8,
              bd=0, command=view_selected).pack(side="right", padx=10)
    kt.Button(header_row,text='delete order',font=("Arial", 12, "bold"),
              bg='green', fg="white", padx=15, pady=8,
              bd=0, command=delete).pack(side="right", padx=10)
    # 3. ORDERS TABLE
    table_card = kt.Frame(content, bg=card_color,
                          highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True)

    cols = ("order_id", "date", "party", "total_items", "total_amt")
    tree = ttk.Treeview(table_card, columns=cols, show="headings")

    headings = ["Order ID", "Date", "Party Name", "Total Items", "Total Amount"]
    for col, head in zip(cols, headings):
        tree.heading(col, text=head)
        tree.column(col, anchor="center")
    
    tree.column("party", width=250, anchor="w")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    # --- LOAD DATA LOGIC ---
    try:
        # Show all PENDING orders
        query = """
        SELECT o.order_id, o.order_date, d.d_name,
               IFNULL(SUM(oi.QTY),0),
               IFNULL(SUM(oi.t_price),0)
        FROM orders o
        JOIN dealer d ON o.d_id = d.d_id
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.status = 'Pending'
        GROUP BY o.order_id
        ORDER BY o.order_id DESC
        """
       
        mycursor.execute(query)
        for row in mycursor.fetchall():
            tree.insert("", "end", values=row)

    except Exception as e:
        print(f"Error loading history: {e}")

def billing_page_frame():
    # Clear the page
    for widget in order_page.winfo_children():
        widget.destroy()
    
    bg_main, sidebar_color, card_color = "#f0f4f8", "#1a365d", "#ffffff"
    accent_blue, text_dark = "#2b6cb0", "#2d3748"
    order_page.config(bg=bg_main)
    show_page(order_page)

    # 1. SIDEBAR
    sidebar = kt.Frame(order_page, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")
    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"),
             bg=sidebar_color, fg="white", pady=25).pack()
    
    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16),
                  bg=sidebar_color, fg="white", bd=0,
                  anchor="w", padx=25, command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT
    content = kt.Frame(order_page, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))
    kt.Label(header_row, text="Billing Management", font=("Arial", 22, "bold"),
             bg=bg_main, fg=text_dark).pack(side="left")

    # --- BILLING LOGIC ---
    def generate_bill():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Selection", "Please select an order to bill.")
            return
        
        order_values = tree.item(selected[0])['values']
        order_id = order_values[0]
        total_amt = order_values[4]
        order_date = order_values[1]
        invoice_no = simpledialog.askstring(
            "Invoice Number",
            f"Enter Invoice Number for Order #{order_id}:"
        )
        
        if invoice_no:
            try:
                # Insert invoice
                query = "INSERT INTO invoices (order_id, invoice_no, t_amount,invoice_date) VALUES (%s, %s, %s,%s)"
                mycursor.execute(query, (order_id, invoice_no, total_amt,order_date))

                # 🔴 FIX: Update order status correctly
                q2 = "UPDATE orders SET status='Completed' WHERE order_id=%s"
                mycursor.execute(q2, (order_id,))

                mydb.commit()

                messagebox.showinfo("Success", f"Invoice {invoice_no} saved successfully!")
                
                # Refresh billing page so billed order disappears
                billing_page_frame()

            except Exception as e:
                mydb.rollback()
                messagebox.showerror("Database Error", f"Could not save invoice: {e}")

    # ACTION BUTTON
    kt.Button(header_row, text="🧾 Generate Bill", font=("Arial", 12, "bold"),
              bg="#ed8936", fg="white", padx=15, pady=8,
              bd=0, command=generate_bill).pack(side="right")

    # 3. TABLE
    table_card = kt.Frame(content, bg=card_color,
                          highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True)

    cols = ("order_id", "date", "party", "total_items", "total_amt")
    tree = ttk.Treeview(table_card, columns=cols, show="headings")

    headings = ["Order ID", "Date", "Party Name", "Total Items", "Total Amount"]
    for col, head in zip(cols, headings):
        tree.heading(col, text=head)
        tree.column(col, anchor="center")

    tree.column("party", width=250, anchor="w")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    # --- LOAD DATA (ONLY PENDING ORDERS) ---
    try:
        query = """
            SELECT o.order_id, o.order_date, d.d_name,
                   IFNULL(SUM(oi.QTY),0),
                   IFNULL(SUM(oi.t_price),0)
            FROM orders o
            JOIN dealer d ON o.d_id = d.d_id
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Pending'
            GROUP BY o.order_id
            ORDER BY o.order_id DESC
        """
        mycursor.execute(query)
        for row in mycursor.fetchall():
            tree.insert("", "end", values=row)

    except Exception as e:
        print(f"Error loading billing data: {e}")


def customer():
    # 1. Clear the frame and setup page
    for widget in cust_more.winfo_children():
        widget.destroy()
    
    # --- THEME COLORS ---
    bg_main, sidebar_color, card_color = "#f0f4f8", "#1a365d", "#ffffff"
    accent_blue, text_dark = "#2b6cb0", "#2d3748"
    
    cust_more.config(bg=bg_main)
    show_page(cust_more)

    # --- LOGIC FUNCTIONS ---
    def stre():
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return
        
        try:
            qry = 'INSERT INTO dealer (d_id, d_name, FOS) VALUES (%s, %s, %s)'
            with open(file_path, 'r') as csvfile:
                reader = c.DictReader(csvfile)
                for row in reader:
                    values = (row['d_id'], row['d_name'], row['FOS'])
                    mycursor.execute(qry, values)
            mydb.commit()
            messagebox.showinfo("Success", "CSV Data Uploaded Successfully!")
            load_dealer_data() # Refresh table
        except Exception as e:
            messagebox.showerror("Upload Error", f"Could not process CSV: {e}")

    def load_dealer_data():
        # Clear existing items in table
        for item in dealer_tree.get_children():
            dealer_tree.delete(item)
        # Fetch from DB
        mycursor.execute("SELECT d_id, d_name, FOS FROM dealer")
        for row in mycursor.fetchall():
            dealer_tree.insert("", "end", values=row)

    # --- 1. SIDEBAR NAVIGATION ---
    sidebar = kt.Frame(cust_more, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")
    
    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"),
             bg=sidebar_color, fg="white", pady=25).pack()

    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]
    
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 13), bg=sidebar_color,
                  fg="white", bd=0, anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # --- 2. MAIN CONTENT AREA ---
    content = kt.Frame(cust_more, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    # Header Row
    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))

    kt.Label(header_row, text="Dealer Management", font=("Arial", 22, "bold"),
             bg=bg_main, fg=text_dark).pack(side="left")

    kt.Button(header_row, text="📤 Upload CSV", font=("Arial", 11, "bold"),
              bg=accent_blue, fg="white", padx=15, pady=8,
              bd=0, command=stre).pack(side="right")

    # --- 3. DEALER TABLE ---
    table_card = kt.Frame(content, bg=card_color, 
                         highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True)

    cols = ("id", "name", "fos")
    dealer_tree = ttk.Treeview(table_card, columns=cols, show="headings")

    dealer_tree.heading("id", text="Dealer ID")
    dealer_tree.heading("name", text="Party / Dealer Name")
    dealer_tree.heading("fos", text="FOS Field")
    
    dealer_tree.column("id", width=100, anchor="center")
    dealer_tree.column("name", width=400, anchor="w")
    dealer_tree.column("fos", width=200, anchor="center")
    
    dealer_tree.pack(fill="both", expand=True, padx=10, pady=10)

    # Scrollbar for table
    scrolly = ttk.Scrollbar(dealer_tree, orient="vertical", command=dealer_tree.yview)
    dealer_tree.configure(yscrollcommand=scrolly.set)
    scrolly.pack(side="right", fill="y")

    # Load initial data
    load_dealer_data()
def report_page_frame():
    # 1. Clear previous widgets
    for widget in order_page.winfo_children():
        widget.destroy()
    
    # --- THEME COLORS ---
    bg_main, sidebar_color, card_color = "#f0f4f8", "#1a365d", "#ffffff"
    accent_blue, text_dark = "#2b6cb0", "#2d3748"
    order_page.config(bg=bg_main)
    show_page(order_page)

    # 1. SIDEBAR NAVIGATION (Unchanged)
    sidebar = kt.Frame(order_page, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")
    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()

    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame),
        ("❌ Exit", window.destroy)
    ]
    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, anchor="w", padx=25, command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(order_page, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    header_row = kt.Frame(content, bg=bg_main)
    header_row.pack(fill="x", pady=(0, 20))
    kt.Label(header_row, text="Sales & Profit Reports", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(side="left")

    # 3. FILTER SECTION
    filter_card = kt.Frame(content, bg=card_color, padx=15, pady=15, 
                           highlightbackground="#cbd5e0", highlightthickness=1)
    filter_card.pack(fill="x", pady=(0, 20))

    kt.Label(filter_card, text="Start Date:", bg=card_color).pack(side="left", padx=5)
    start_date_ent = kt.Entry(filter_card, width=12)
    start_date_ent.insert(0, str(a))
    start_date_ent.pack(side="left", padx=5)

    kt.Label(filter_card, text="End Date:", bg=card_color).pack(side="left", padx=5)
    end_date_ent = kt.Entry(filter_card, width=12)
    end_date_ent.insert(0, str(a))
    end_date_ent.pack(side="left", padx=5)

    # 4. KPI CARDS
    kpi_frame = kt.Frame(content, bg=bg_main)
    kpi_frame.pack(fill="x", pady=10)

    def create_kpi_card(parent, title, value, color):
        card = kt.Frame(parent, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1, padx=20, pady=15)
        card.pack(side="left", expand=True, fill="both", padx=5)
        kt.Label(card, text=title, font=("Arial", 10, "bold"), bg=card_color, fg="#718096").pack(anchor="w")
        lbl = kt.Label(card, text=value, font=("Arial", 18, "bold"), bg=card_color, fg=color)
        lbl.pack(anchor="w", pady=5)
        return lbl

    rev_lbl = create_kpi_card(kpi_frame, "TOTAL REVENUE", "₹ 0.00", accent_blue)
    prof_lbl = create_kpi_card(kpi_frame, "EST. PROFIT", "₹ 0.00", "#38a169")
    ord_lbl = create_kpi_card(kpi_frame, "ORDERS COUNT", "0", text_dark)

    # 5. MAIN DATA TABLE (Removed Product & Qty)
    table_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1)
    table_card.pack(fill="both", expand=True, pady=10)

    # We include 'id' but we can hide it or keep it for the query logic
    cols = ("Order_id","Invoice_no", "date", "dealer", "revenue", "profit")
    tree = ttk.Treeview(table_card, columns=cols, show="headings", height=8)
    tree.heading("Order_id", text="ORDER ID")
    tree.heading("Invoice_no", text="INVOICE NO")
    tree.heading("date", text="DATE")
    tree.heading("dealer", text="DEALER NAME")
    tree.heading("revenue", text="REVENUE")
    tree.heading("profit", text="PROFIT")

    for col in cols: tree.column(col, anchor="center")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    # 6. ORDER ITEMS SECTION (Only visible details here)
    kt.Label(content, text="ORDER ITEMS DETAILS", font=("Arial", 12, "bold"), bg=bg_main, fg=text_dark).pack(anchor="w", pady=(10, 0))
    details_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1)
    details_card.pack(fill="x", pady=10)

    details_cols = ("product_name", "quantity")
    details_tree = ttk.Treeview(details_card, columns=details_cols, show="headings", height=4)
    details_tree.heading("product_name", text="PRODUCT NAME")
    details_tree.heading("quantity", text="QTY")
    details_tree.column("product_name", anchor="w", width=450)
    details_tree.column("quantity", anchor="center", width=100)
    details_tree.pack(fill="x", padx=10, pady=10)

    # Logic: When a row is selected, fetch all items for that Order ID
    def on_tree_select(event):
        for i in details_tree.get_children(): details_tree.delete(i)
        selected_item = tree.selection()
        if selected_item:
            order_id = tree.item(selected_item)['values'][0]
            try:
                # Query to fetch all products for the selected order
                item_query = """
                    SELECT p.product_name, oi.QTY 
                    FROM order_items oi 
                    JOIN product p ON oi.product_id = p.product_id 
                    WHERE oi.order_id = %s
                """
                mycursor.execute(item_query, (order_id,))
                items = mycursor.fetchall()
                for item in items:
                    details_tree.insert("", "end", values=item)
            except Exception as e:
                print(f"Detail Fetch Error: {e}")

    tree.bind("<<TreeviewSelect>>", on_tree_select)

    # --- UPDATED REPORT LOGIC ---
    def generate_report():
        sd, ed = start_date_ent.get(), end_date_ent.get()
        for i in tree.get_children(): tree.delete(i)
        
        try:
            # FIX: Grouping ONLY by order_id to prevent duplicates across different dates
            query = """
                SELECT
                    o.order_id,
                    GROUP_CONCAT(DISTINCT i.invoice_no SEPARATOR ', ') AS invoice_no,
                    MIN(o.order_date) AS display_date,
                    d.d_name,
                    SUM(oi.t_price) AS total_revenue,
                    SUM(oi.t_price - (oi.QTY * p.p_rate)) AS total_profit
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                JOIN product p ON oi.product_id = p.product_id
                JOIN invoices i ON i.order_id = o.order_id
                LEFT JOIN dealer d ON o.d_id = d.d_id
                WHERE o.order_date BETWEEN %s AND %s AND o.status = 'Completed'
                GROUP BY
                    o.order_id,
                    d.d_name
                ORDER BY display_date DESC
            """
            mycursor.execute(query, (sd, ed))
            rows = mycursor.fetchall()

            total_rev = 0.0
            total_prof = 0.0

            for row in rows:
                tree.insert("", "end", values=row)
                total_rev += float(row[4])   # total_revenue
                total_prof += float(row[5])  # total_profit

            rev_lbl.config(text=f"₹ {total_rev:,.2f}")
            prof_lbl.config(text=f"₹ {total_prof:,.2f}")
            ord_lbl.config(text=str(len(rows)))

        except Exception as e:
            messagebox.showerror("Report Error", f"SQL Error: {e}")

    kt.Button(filter_card, text="📊 Generate Report", bg=accent_blue, fg="white", 
              command=generate_report, padx=15).pack(side="left", padx=20)
    
    generate_report()
# Example of dynamic sidebar button generation
def settings_page_frame():
    # 1. Clear previous widgets
    for widget in order_page.winfo_children():
        widget.destroy()
    
    # --- THEME COLORS ---
    bg_main, sidebar_color, card_color = "#f0f4f8", "#1a365d", "#ffffff"
    accent_blue, text_dark = "#2b6cb0", "#2d3748"
    order_page.config(bg=bg_main)
    show_page(order_page)

    # 1. SIDEBAR (Navigation)
    sidebar = kt.Frame(order_page, bg=sidebar_color, width=220)
    sidebar.pack(side="left", fill="y")
    kt.Label(sidebar, text="Nitya Sales", font=("Arial", 16, "bold"), 
             bg=sidebar_color, fg="white", pady=25).pack()

    nav_btns = [
        ("🏠 Dashboard", lambda: [build_dashboard(), show_page(dash_frame)]),
        ("📦 Products", view_table), 
        ("📊 Inventory", master_function),
        ("👥 Dealers", customer),           # 👈 Added Dealer Management
        ("🛒 Orders", order_page_frame), 
        ("🧾 Billings", billing_page_frame),
        ("📈 Reports", report_page_frame), 
        ("⚙️ Settings", settings_page_frame), # Admin Only (if applicable)
        ("❌ Exit", window.destroy)
    ]

    for text, cmd in nav_btns:
        kt.Button(sidebar, text=text, font=("Arial", 16), bg=sidebar_color, 
                  fg="white", bd=0, activebackground=accent_blue, 
                  activeforeground="white", anchor="w", padx=25,
                  command=cmd).pack(fill="x", pady=5)

    # 2. MAIN CONTENT AREA
    content = kt.Frame(order_page, bg=bg_main, padx=30, pady=25)
    content.pack(side="right", fill="both", expand=True)

    kt.Label(content, text="User Access Control", font=("Arial", 22, "bold"), 
             bg=bg_main, fg=text_dark).pack(anchor="w", pady=(0, 20))

    # --- USER LIST TABLE ---
    list_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1)
    list_card.pack(fill="x", pady=10)

    cols = ("id", "username", "role", "permissions")
    user_tree = ttk.Treeview(list_card, columns=cols, show="headings", height=5)
    for col in cols:
        user_tree.heading(col, text=col.upper())
        user_tree.column(col, anchor="center")
    user_tree.pack(fill="x", padx=10, pady=10)

    def load_users():
        for i in user_tree.get_children(): user_tree.delete(i)
        mycursor.execute("SELECT user_id, username, role, permissions FROM users")
        for row in mycursor.fetchall():
            user_tree.insert("", "end", values=row)

    load_users()

    # --- PERMISSIONS EDITING SECTION ---
    edit_card = kt.Frame(content, bg=card_color, highlightbackground="#cbd5e0", highlightthickness=1, padx=20, pady=20)
    edit_card.pack(fill="both", expand=True, pady=10)

    kt.Label(edit_card, text="Edit Permissions for Selected User", font=("Arial", 12, "bold"), bg=card_color).pack(anchor="w")

    # Checkboxes for pages
    available_pages = ["Dashboard", "Products", "Inventory", "Orders", "Billings", "Reports", "Settings"]
    check_vars = {}
    cb_container = kt.Frame(edit_card, bg=card_color)
    cb_container.pack(fill="x", pady=15)

    for i, p_name in enumerate(available_pages):
        var = kt.BooleanVar()
        cb = kt.Checkbutton(cb_container, text=p_name, variable=var, bg=card_color, font=("Arial", 10))
        cb.grid(row=i//4, column=i%4, sticky="w", padx=20, pady=5)
        check_vars[p_name] = var

    def on_user_select(event):
        selected = user_tree.selection()
        if not selected: return
        user_perms = str(user_tree.item(selected[0])['values'][3]).split(',')
        
        for p_name, var in check_vars.items():
            var.set(p_name in user_perms)

    user_tree.bind("<<TreeviewSelect>>", on_user_select)

    # --- UPDATE BUTTON ---
    def update_permissions():
        selected = user_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a user first.")
            return
        
        u_id = user_tree.item(selected[0])['values'][0]
        new_perms = [p for p, v in check_vars.items() if v.get()]
        perms_string = ",".join(new_perms)

        try:
            mycursor.execute("UPDATE users SET permissions=%s WHERE user_id=%s", (perms_string, u_id))
            mydb.commit()
            messagebox.showinfo("Success", "Permissions updated successfully!")
            load_users()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    kt.Button(edit_card, text="💾 Save Changes", bg=accent_blue, fg="white", 
              font=("Arial", 11, "bold"), command=update_permissions, padx=20, pady=10).pack(pady=10)
def login_screen():
    # 1. Setup the login container inside the main container
    # We use grid so it occupies the same 'stack' as the dashboard
    login_container = kt.Frame(container, bg="#1a365d")
    login_container.grid(row=0, column=0, sticky="nsew")
    
    # Ensure this frame is visible immediately
    show_page(login_container)

    # --- LOGIN CARD ---
    login_card = kt.Frame(login_container, bg="white", padx=40, pady=40, 
                          highlightthickness=1, highlightbackground="#cbd5e0")
    login_card.place(relx=0.5, rely=0.5, anchor="center")

    kt.Label(login_card, text="Nitya Sales Login", font=("Arial", 18, "bold"), 
             bg="white", fg="#2d3748").pack(pady=(0, 20))

    # Username
    kt.Label(login_card, text="Username", bg="white", font=("Arial", 10, "bold"), 
             fg="#718096").pack(anchor="w")
    u_ent = kt.Entry(login_card, font=("Arial", 12), width=30, bd=1, relief="solid")
    u_ent.pack(pady=(5, 15))

    # Password
    kt.Label(login_card, text="Password", bg="white", font=("Arial", 10, "bold"), 
             fg="#718096").pack(anchor="w")
    p_ent = kt.Entry(login_card, font=("Arial", 12), width=30, bd=1, relief="solid", show="*")
    p_ent.pack(pady=(5, 20))

    def attempt_login():
        global current_user
        
        username = u_ent.get()
        password = p_ent.get()

        try:
            mycursor.execute("SELECT user_id, username, role, permissions FROM users WHERE username=%s AND password=%s", 
                             (username, password))
            res = mycursor.fetchone()

            if res:
                # 1. Setup the session
                current_user = {
                    'id': res[0],
                    'username': res[1],
                    'role': res[2],
                    'permissions': res[3] if res[3] else ""
                }

                # 2. SUCCESS: Destroy the login screen so it's gone from memory
                login_container.destroy()
                
                # 3. Build and show the dashboard
                build_dashboard()
                show_page(dash_frame) 
                
            else:
                messagebox.showerror("Login Failed", "Invalid credentials. Please try again.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Login Error: {e}")

    # Login Button
    kt.Button(login_card, text="Sign In", command=attempt_login, bg="#2b6cb0", fg="white", 
              font=("Arial", 12, "bold"), bd=0, cursor="hand2", padx=20, pady=10).pack(fill="x")
def build_sidebar(parent):
    # Only show buttons if the page name is in the user's permission string
    for text, cmd, page_id in nav_data:
        if page_id in current_user['permissions']:
            kt.Button(parent, text=text, command=cmd).pack()
def master_function():
    change_data()
    view_table_stock()  
def show_page(frame):
    frame.tkraise()
# -------------------- START APPLICATION --------------------
login_screen()
window.mainloop()
