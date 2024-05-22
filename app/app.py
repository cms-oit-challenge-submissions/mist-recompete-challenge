import os
import urwid
import urwid.numedit
import warnings
import sqlite3
from dataclasses import dataclass

warnings.filterwarnings("ignore")

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "inventory.db")


@dataclass
class InventoryItem:
    id: int
    name: str
    quantity: int
    price: float


class InventoryManager:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE)
        self.c = self.conn.cursor()
        self.items = self.load_items()
        self.selected_item_index = None
        self.checkout_warning = None
        self.checkout_items = []
        self.header = urwid.Text("Inventory Manager")
        self.home_screen()

    def load_items(self):
        self.c.execute("SELECT * FROM inventory")
        return [InventoryItem(*row) for row in self.c.fetchall()]

    def get_item_buttons(self, on_press):
        items = []
        for item_index, item in enumerate(self.items):
            items.append(
                urwid.Button(
                    f"{item.name} (Qty: {item.quantity})",
                    on_press=lambda btn, idx=item_index: on_press(btn, idx),
                )
            )
        if len(items) == 0:
            items = [urwid.Text("No items available")]
        return items

    def home_screen(self):
        self.view = urwid.Frame(urwid.Text(""), header=self.header)
        self.home_menu()

    def home_menu(self):
        self.view.body = urwid.Filler(
            urwid.Pile(
                [
                    urwid.Text("Welcome to the Inventory Manager!\n\n"),
                    urwid.Button("Check out", on_press=self.checkout_screen),
                    urwid.Button("Manage inventory", on_press=self.manage_inventory),
                    urwid.Button("Quit", on_press=self.exit_program),
                ]
            )
        )

    def checkout_screen(self, *args):
        items = self.get_item_buttons(self.select_checkout_item)

        checkout_items = [
            urwid.Text(
                f"(${item['price'] * item['quantity']:.3f}) - {item['quantity']}: {item['item'].name}"
            )
            for item in self.checkout_items
        ]
        if len(checkout_items) == 0:
            checkout_items = [urwid.Text("No items selected")]

        if self.selected_item_index is None:
            self.quantity_field = urwid.Text("Select an item")
        else:
            self.quantity_field = urwid.IntEdit(
                f"Enter {self.items[self.selected_item_index].name} quantity: ",
                default=0,
            )

        total_cost = float(
            sum((item["price"] * item["quantity"]) for item in self.checkout_items)
        )

        self.view.body = urwid.Pile(
            [
                (
                    "flow",
                    urwid.Columns(
                        [
                            (
                                "weight",
                                1,
                                urwid.Button(
                                    "Complete check out",
                                    on_press=self.complete_checkout,
                                ),
                            ),
                            (
                                "weight",
                                1,
                                urwid.Button(
                                    "Check out item",
                                    on_press=self.enter_checkout_item_quantity,
                                ),
                            ),
                        ]
                    ),
                ),
                (
                    "flow",
                    urwid.Columns(
                        [
                            ("weight", 1, urwid.Text(f"Total: ${total_cost:.3f}")),
                            (
                                "weight",
                                1,
                                urwid.Pile(
                                    [
                                        self.quantity_field,
                                        urwid.Text(self.checkout_warning or ""),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
                urwid.Columns(
                    [
                        (
                            "weight",
                            1,
                            urwid.LineBox(
                                urwid.ListBox(
                                    urwid.SimpleFocusListWalker(checkout_items)
                                )
                            ),
                        ),
                        (
                            "weight",
                            1,
                            urwid.LineBox(
                                urwid.ListBox(urwid.SimpleFocusListWalker(items))
                            ),
                        ),
                    ]
                ),
            ]
        )

    def select_checkout_item(self, btn, index):
        self.selected_item_index = index
        self.checkout_warning = None
        self.checkout_screen()

    def enter_checkout_item_quantity(self, button=None):
        if self.selected_item_index is None:
            self.checkout_warning = "No item selected"
            self.checkout_screen()
            return
        quantity = int(self.quantity_field.get_edit_text())
        if quantity > self.items[self.selected_item_index].quantity:
            self.checkout_warning = "Not enough inventory is available"
        else:
            item_subtotal = self.items[self.selected_item_index].price * quantity
            self.checkout_items.append(
                {
                    "item": self.items[self.selected_item_index],
                    "quantity": quantity,
                    "price": item_subtotal,
                }
            )
            self.selected_item_index = None
            self.checkout_warning = None
        self.checkout_screen()

    def complete_checkout(self, button=None):
        for checkout_item in self.checkout_items:
            self.c.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE id = ?",
                (checkout_item["quantity"], checkout_item["item"].id),
            )
        self.conn.commit()
        self.items = self.load_items()
        self.selected_item_index = None
        self.checkout_items = []
        self.checkout_warning = None
        self.home_menu()

    def manage_inventory(self, arg=None):
        items = self.get_item_buttons(self.select_edit_item)
        self.view.body = urwid.Pile(
            [
                (
                    "flow",
                    urwid.Text(
                        "\nInstructions:\n"
                        "- Click on an item to edit, delete, or check out"
                    ),
                ),
                urwid.LineBox(
                    urwid.ListBox(urwid.SimpleFocusListWalker(items)),
                ),
                (
                    "flow",
                    urwid.Columns(
                        [
                            urwid.Button(
                                "Add",
                                on_press=lambda a: self.edit_item_dialog(self.add_item),
                            ),
                            urwid.Button("Home", on_press=lambda a: self.home_menu()),
                        ]
                    ),
                ),
            ]
        )

    def select_edit_item(self, btn, index):
        self.selected_item_index = index
        self.edit_item_dialog(self.edit_item, self.items[self.selected_item_index])

    def edit_item_dialog(self, on_done, item=None):
        response = urwid.Text("Enter the name and quantity of the new item:\n")
        self.name_field = urwid.Edit("Name: ", item.name if item else "")
        self.quantity_field = urwid.IntEdit("Quantity: ", item.quantity if item else "")
        self.price_field = urwid.Edit("Price: $", str(item.price) if item else "")
        if item:
            bottom_controls = (
                "flow",
                urwid.Columns(
                    [
                        urwid.Button(
                            "Save",
                            on_press=on_done,
                        ),
                        urwid.Button(
                            "Delete",
                            on_press=self.delete_item,
                        ),
                    ]
                ),
            )
        else:
            bottom_controls = urwid.Button(
                "Save",
                on_press=on_done,
            )
        self.view.body = urwid.Filler(
            urwid.Pile(
                [
                    response,
                    bottom_controls,
                    self.name_field,
                    self.price_field,
                    self.quantity_field,
                ]
            )
        )

    def add_item(self, button=None):
        name = self.name_field.edit_text
        quantity = int(self.quantity_field.edit_text)
        price = float(self.price_field.edit_text)
        self.c.execute(
            f"INSERT INTO inventory (name, quantity, price) VALUES ('{name}', {quantity}, {price})",
        )
        self.conn.commit()
        self.items = self.load_items()
        self.manage_inventory()

    def edit_item(self, button=None):
        self.c.execute(
            f"UPDATE inventory SET name = '{self.name_field.edit_text}', "
            f"quantity = {int(self.quantity_field.edit_text)}, "
            f"price = {float(self.price_field.edit_text)} "
            f"WHERE id = {self.items[self.selected_item_index].id}",
        )
        self.conn.commit()
        self.items = self.load_items()
        self.selected_item_index = None
        self.manage_inventory()

    def delete_item(self, button=None):
        self.c.execute(
            "DELETE FROM inventory WHERE id = ?",
            (self.items[self.selected_item_index].id,),
        )
        self.conn.commit()
        self.items = self.load_items()
        self.selected_item_index = None
        self.manage_inventory()

    def exit_program(self, button):
        raise urwid.ExitMainLoop()

    def run(self):
        top = urwid.Padding(self.view, left=2, right=2)
        urwid.MainLoop(
            top, palette=[("reversed", "standout", ""), ("menu", "black", "light gray")]
        ).run()


if __name__ == "__main__":
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory
        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, quantity INTEGER, price REAL)
        """
    )
    conn.commit()

    c.execute("SELECT * FROM inventory")
    items = c.fetchall()
    if len(items) == 0:
        c.execute(
            "INSERT INTO inventory (name, quantity, price) VALUES ('Apple', 10, 0.5)"
        )
        c.execute(
            "INSERT INTO inventory (name, quantity, price) VALUES ('Banana', 5, 10.0)"
        )
        c.execute(
            "INSERT INTO inventory (name, quantity, price) VALUES ('Orange', 8, 1.0)"
        )
        conn.commit()

    conn.close()

    manager = InventoryManager()
    manager.run()
