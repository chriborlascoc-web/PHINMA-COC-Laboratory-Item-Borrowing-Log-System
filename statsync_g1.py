import datetime # handles dates and times, such as borrowing, returning, and log time
import re # expression used to validate the format of users credentials

# ==================== IN-MEMORY "DATABASE" ====================

borrow_records = []   # list of every borrow/return record
activity_logs = []    # list of logged action dicts

accounts = {
    "guard": [
        {"username": "guard1", "password": "guard123"},
    ],
}

# Equipment the security guard holds, with the TOTAL quantity of each item.
equipment_stock = {
    "CL1 Key": 1,
    "CL2 Key": 1,
    "CL3 Key": 1,
    "CL4 Key": 1,
    "CL5 Key": 1,
    "TV Remote": 5,
    "Aircon Remote": 10,
}

# An item held longer than this many minutes is flagged OVERDUE.
OVERDUE_MINUTES = 120

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ==================== HELPER FUNCTIONS ====================

def now():
    return datetime.datetime.now().strftime(TIME_FORMAT)


def minutes_since(timestamp):
    started = datetime.datetime.strptime(timestamp, TIME_FORMAT)
    return int((datetime.datetime.now() - started).total_seconds() // 60)


def log_action(actor_role, actor_name, action):
    activity_logs.append({
        "timestamp": now(),
        "role": actor_role,
        "actor": actor_name,
        "action": action,
    })


# ---------------- INPUT VALIDATION HELPERS ----------------
# Each one loops until the input is valid, then returns the cleaned value.

def get_non_empty_input(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field can't be empty. Please try again.")


NAME_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z.'\- ]*,\s*[A-Za-z][A-Za-z.'\- ]*(,\s*[A-Za-z]\.?)?$"
)


def get_valid_full_name(prompt):
    while True:
        value = input(prompt).strip()
        if NAME_PATTERN.match(value):
            return value
        print("Please enter the name as: Last Name, First Name, Middle Initial "
              "(e.g. Dela Cruz, Juan, M.) -- Middle Initial is optional: "
              "Dela Cruz, Juan")


def get_valid_menu_choice(prompt, valid_options):
    while True:
        choice = input(prompt).strip()
        if choice in valid_options:
            return choice
        print(f"Invalid option. Please choose one of: {', '.join(sorted(valid_options))}")


def confirm_yes_no(prompt):
    return get_valid_menu_choice(prompt, {"1", "2"}) == "1"


def ask_record_id(prompt, pool):
    valid_ids = {r["record_id"] for r in pool}
    while True:
        value = input(prompt).strip().upper()
        if value == "0":
            return None
        if value in valid_ids:
            return value
        print("Invalid Record ID. Enter one from the list above (or 0 to cancel).")


def ask_quantity(prompt):
    while True:
        value = input(prompt).strip()
        if value.isdigit() and int(value) >= 1:
            return int(value)
        print("Please enter a whole number of 1 or more.")


def ask_stock_item(prompt):
    # Only accepts items already in the equipment list.
    # New equipment is added separately via the guard menu ("Add Equipment").
    while True:
        value = input(prompt).strip()
        if value == "0":
            return None
        if not value:
            print("This field can't be empty. Please try again.")
            continue
        name = find_stock_item(value)
        if name:
            return name
        print(f"\n'{value}' is not in the equipment list. "
              "Use option 7 (Add Equipment) in the guard menu to add it first.")


# ---------------- LOOKUP / DISPLAY HELPERS ----------------

def get_borrowed_records():
    return [r for r in borrow_records if r["status"] == "Borrowed"]


def find_stock_item(item_name):
    # Returns the item's official name from equipment_stock (ignores capitalization).
    for name in equipment_stock:
        if name.lower() == item_name.lower():
            return name
    return None


def get_item_borrowers(item_name):
    # Every record of this item that is still marked "Borrowed".
    return [r for r in get_borrowed_records() if r["item_name"].lower() == item_name.lower()]


def get_available_count(item_name):
    return equipment_stock[item_name] - len(get_item_borrowers(item_name))


def print_borrowed(records, title):
    if not records:
        print("\nNo items to show.")
        return
    print(f"\n--- {title} ---")
    for r in records:
        mins = minutes_since(r["time_out"])
        line = (f"{r['record_id']} | {r['item_name']} | Held by: {r['faculty']} "
                f"since {r['time_out']} ({mins} min)")
        if mins > OVERDUE_MINUTES:
            line += "  [OVERDUE]"
        print(line)


def print_record(r):
    print(f"\nRecord ID: {r['record_id']}")
    print(f"  Item: {r['item_name']}")
    print(f"  Faculty: {r['faculty']}")
    print(f"  Borrowed: {r['time_out']}")
    if r["status"] == "Returned":
        print(f"  Returned: {r['time_in']} ({r['minutes_held']} min)")
    else:
        print("  Returned: Not yet returned")
    print(f"  Released by: {r['released_by']}")


# ==================== LOGIN (Security Guard) ====================

def account_login(role):
    account_list = accounts[role]
    print(f"\n--- {role.upper()} LOGIN ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    for acc in account_list:
        if acc["username"] == username and acc["password"] == password:
            log_action(role.capitalize(), username, "Logged in")
            return username
    print("Invalid credentials.")
    return None


# ==================== SECURITY GUARD (PRIMARY USER) ====================

def guard_menu(username):
    while True:
        print(f"\n=== SECURITY GUARD MENU ({username}) ===")
        print("1. Check Out (lend an item)")
        print("2. Check In (receive a returned item)")
        print("3. View Currently Borrowed Items")
        print("4. View Overdue Items")
        print("5. Search Borrow History by Faculty")
        print("6. View Equipment Stock (quantity)")
        print("7. Add Equipment")
        print("8. Logout")
        choice = get_valid_menu_choice("Choose an option: ", {"1", "2", "3", "4", "5", "6", "7", "8"})
        if choice == "1":
            check_out(username)
        elif choice == "2":
            check_in(username)
        elif choice == "3":
            print_borrowed(get_borrowed_records(), "CURRENTLY BORROWED ITEMS")
        elif choice == "4":
            view_overdue()
        elif choice == "5":
            search_history()
        elif choice == "6":
            view_stock()
        elif choice == "7":
            add_equipment(username)
        elif choice == "8":
            log_action("Guard", username, "Logged out")
            print("Logging out...")
            break


def check_out(guard):
    print("\n--- CHECK OUT ---")
    view_stock()
    item_name = ask_stock_item("\nItem to borrow (type the name, 0 to cancel): ")
    if item_name is None:
        print("\nCancelled. No changes were made.")
        return

    # Notice: stop if every unit of this item is already out.
    holders = get_item_borrowers(item_name)
    available = get_available_count(item_name)
    if available <= 0:
        print(f"\nNOTICE: '{item_name}' is currently borrowed. All {equipment_stock[item_name]} "
              f"unit(s) are out and nothing is left to lend.")
        for r in holders:
            print(f"  - With {r['faculty']} since {r['time_out']} (Record ID: {r['record_id']})")
        print("\nNo changes were made.")
        return
    print(f"\n'{item_name}': {available} of {equipment_stock[item_name]} unit(s) available.")

    faculty = get_valid_full_name("Faculty name (Last Name, First Name): ")

    print("\n--- CONFIRM CHECK OUT ---")
    print(f"  Item: {item_name}")
    print(f"  Faculty: {faculty}")
    if not confirm_yes_no("Confirm? (1 = Yes, 2 = No, cancel): "):
        print("\nCancelled. No changes were made.")
        return

    record_id = f"REC-{len(borrow_records) + 1:04d}"
    borrow_records.append({
        "record_id": record_id,
        "item_name": item_name,
        "faculty": faculty,
        "time_out": now(),
        "time_in": None,
        "minutes_held": None,
        "released_by": guard,
        "status": "Borrowed",
    })
    log_action("Guard", guard, f"Checked out '{item_name}' to {faculty} ({record_id})")
    print(f"\nDone! '{item_name}' is now with {faculty}. Record ID: {record_id}")


def check_in(guard):
    borrowed = get_borrowed_records()
    if not borrowed:
        print("\nNo items are currently borrowed.")
        return
    print_borrowed(borrowed, "CURRENTLY BORROWED ITEMS")
    record_id = ask_record_id("\nEnter Record ID being returned (0 to cancel): ", borrowed)
    if record_id is None:
        print("\nCancelled. No changes were made.")
        return

    for r in borrowed:
        if r["record_id"] == record_id:
            held = minutes_since(r["time_out"])
            r["time_in"] = now()
            r["minutes_held"] = held
            r["status"] = "Returned"
            log_action("Guard", guard, f"Checked in '{r['item_name']}' from {r['faculty']} after {held} min ({record_id})")
            print(f"\nDone! '{r['item_name']}' was returned by {r['faculty']} (held {held} min).")
            if held > OVERDUE_MINUTES:
                print(f"Note: this was held longer than {OVERDUE_MINUTES} minutes.")
            return


def view_overdue():
    overdue = [r for r in get_borrowed_records() if minutes_since(r["time_out"]) > OVERDUE_MINUTES]
    if not overdue:
        print(f"\nNo overdue items (limit: {OVERDUE_MINUTES} minutes).")
        return
    print_borrowed(overdue, f"OVERDUE ITEMS (over {OVERDUE_MINUTES} minutes)")


def view_stock():
    if not equipment_stock:
        print("\nNo equipment in the stock list.")
        return
    print("\n--- EQUIPMENT STOCK ---")
    width = max(len(name) for name in equipment_stock)
    for name, total in equipment_stock.items():
        borrowed = len(get_item_borrowers(name))
        available = total - borrowed
        line = f"{name.ljust(width)} - Total: {total} | Borrowed: {borrowed} | Available: {available}"
        if available <= 0:
            line += "  [ALL BORROWED]"
        print(line)


def add_equipment(guard):
    print("\n--- ADD EQUIPMENT ---")
    view_stock()
    while True:
        value = input("\nItem name (0 to cancel): ").strip()
        if value == "0":
            print("\nCancelled. No changes were made.")
            return
        if not value:
            print("This field can't be empty. Please try again.")
            continue
        break

    existing = find_stock_item(value)
    if existing:
        # Item is already listed: offer to add more units to its total.
        print(f"\n'{existing}' is already in the list (total: {equipment_stock[existing]}).")
        if not confirm_yes_no("Add more units to it? (1 = Yes, 2 = No, cancel): "):
            print("\nCancelled. No changes were made.")
            return
        quantity = ask_quantity("Number of units to add: ")
        equipment_stock[existing] += quantity
        total = equipment_stock[existing]
        log_action("Guard", guard, f"Added {quantity} unit(s) to '{existing}' (new total {total})")
        print(f"\nDone! '{existing}' now has {total} unit(s).")
        return

    quantity = ask_quantity("Total quantity of this item: ")
    equipment_stock[value] = quantity
    log_action("Guard", guard, f"Added '{value}' to the equipment list (quantity {quantity})")
    print(f"\nDone! Added '{value}' - {quantity} unit(s).")


def search_history():
    name = get_non_empty_input("\nEnter faculty name to search: ").lower()
    matches = [r for r in borrow_records if name in r["faculty"].lower()]
    if not matches:
        print("No matching records.")
        return
    for r in matches:
        print_record(r)


# ==================== FACULTY (SECONDARY USER) ====================

def faculty_login():
    print("\n--- FACULTY LOGIN ---")
    name = get_valid_full_name("Enter your name (Last Name, First Name): ")
    log_action("Faculty", name, "Logged in")
    faculty_menu(name)


def faculty_menu(name):
    while True:
        print(f"\n=== FACULTY MENU ({name}) ===")
        print("1. Check Who Currently Has The Item")
        print("2. View My Borrow History")
        print("3. Exit")
        choice = get_valid_menu_choice("Choose an option: ", {"1", "2", "3"})
        if choice == "1":
            print_borrowed(get_borrowed_records(), "CURRENTLY BORROWED ITEMS")
        elif choice == "2":
            view_my_history(name)
        elif choice == "3":
            log_action("Faculty", name, "Exited faculty menu")
            print("Exiting faculty menu...")
            break


def view_my_history(name):
    mine = [r for r in borrow_records if r["faculty"].lower() == name.lower()]
    if not mine:
        print("\nYou have no borrow records yet.")
        return
    print("\n--- YOUR BORROW HISTORY ---")
    for r in mine:
        print_record(r)


# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("   PHINMA COC LABORATORY EQUIPMENT BORROWING LOG SYSTEM")
    print("=" * 60)
    while True:
        print("\nSelect user type:")
        print("1. Security Guard")
        print("2. Faculty")
        print("3. Exit")
        choice = get_valid_menu_choice("Choose an option: ", {"1", "2", "3"})
        if choice == "1":
            username = account_login("guard")
            if username:
                guard_menu(username)
        elif choice == "2":
            faculty_login()
        elif choice == "3":
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()