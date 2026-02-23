#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author      : Ravi Karra
Date        : 2026-02-19
Subject     : Warehouse Order Status Automation (End-to-End)
Project Type: pilot
"""

from __future__ import annotations

import argparse
import csv
import datetime
import random
import string
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ----------------------------- Domain Constants & Helpers ----------------------------- #

STATUS_ITEM_IN_PROCESS = "item in process of the order"
STATUS_READY_TO_PACK = "ready to pack"
STATUS_PACKAGE_LABELLED = "package labelled"
STATUS_READY_TO_BE_PICKED = "ready to be picked"
STATUS_AWAITING_APPROVAL = "awaiting manager approval"
STATUS_APPROVAL_DECLINED = "declined by manager"
STATUS_APPROVAL_GRANTED = "approved by manager"
STATUS_PACKAGE_LOADED = "package loaded"

STATION_WAREHOUSE_RACKS = "warehouse-racks"
STATION_PACKING = "packing-station"
STATION_SORTING = "sorting-collation-station"
STATION_AUDIT = "manager-audit-station"
STATION_LOADING = "truck-loading-dock"

LEDGER_CSV = "ledger.csv"


def now_iso() -> str:
    """Return current timestamp in ISO-8601 format for consistent logs."""
    return datetime.datetime.now().isoformat(timespec="seconds")


def random_barcode(n: int = 12) -> str:
    """Generate a pseudo barcode (alphanumeric) for demo purposes."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


# ----------------------------- Data Models ----------------------------- #

@dataclass
class Item:
    """Represents a physical SKU/item in the warehouse."""
    sku: str
    description: str
    rack: Optional[str] = None  # Current rack if at racks; None when at stations
    location: str = STATION_WAREHOUSE_RACKS  # Logical location/station
    barcode: Optional[str] = None  # Assigned during labelling


@dataclass
class ShippingLabel:
    """Represents the shipping label content attached at packing."""
    from_address: str
    to_address: str
    barcode: str


@dataclass
class Order:
    """Represents a customer order being processed on the floor."""
    order_id: str
    item: Item
    current_status: str = STATUS_ITEM_IN_PROCESS
    status_history: List[Tuple[str, str]] = field(default_factory=list)
    label: Optional[ShippingLabel] = None

    def update_status(self, new_status: str) -> None:
        """Transition the order to a new status and log the timestamped change."""
        self.current_status = new_status
        self.status_history.append((now_iso(), new_status))


# ----------------------------- Ledger ----------------------------- #

class RackLedger:
    """A simple in-memory ledger to help floor engineers locate items on racks."""

    def __init__(self, persist_csv: bool = True) -> None:
        self.racks: Dict[str, List[str]] = {}
        self.locations: Dict[str, str] = {}
        self.persist_csv = persist_csv
        if self.persist_csv:
            self._init_csv()

    def _init_csv(self) -> None:
        with open(LEDGER_CSV, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "sku", "location", "rack_contents_snapshot"])

    def _snapshot_rack(self, rack_id: str) -> str:
        items = self.racks.get(rack_id, [])
        return f"{rack_id}: {items}"

    def _log_csv(self, sku: str, location: str, rack_id: Optional[str] = None) -> None:
        if not self.persist_csv:
            return
        snapshot = self._snapshot_rack(rack_id) if rack_id else ""
        with open(LEDGER_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([now_iso(), sku, location, snapshot])

    def register_rack(self, rack_id: str) -> None:
        self.racks.setdefault(rack_id, [])

    def add_item_to_rack(self, sku: str, rack_id: str) -> None:
        self.register_rack(rack_id)
        if sku not in self.racks[rack_id]:
            self.racks[rack_id].append(sku)
        self.locations[sku] = f"{STATION_WAREHOUSE_RACKS}:{rack_id}"
        self._log_csv(sku, self.locations[sku], rack_id=rack_id)

    def remove_item_from_rack(self, sku: str, rack_id: str, new_location: str) -> None:
        if sku in self.racks.get(rack_id, []):
            self.racks[rack_id].remove(sku)
        self.locations[sku] = new_location
        self._log_csv(sku, new_location, rack_id=rack_id)

    def update_item_location(self, sku: str, new_location: str) -> None:
        self.locations[sku] = new_location
        self._log_csv(sku, new_location)

    def find_item(self, sku: str) -> Optional[str]:
        return self.locations.get(sku)

    def pretty_print(self) -> None:
        print("\n=== LEDGER SNAPSHOT ===")
        for rack_id, items in sorted(self.racks.items()):
            print(f"  Rack {rack_id}: {items}")
        print("  Item Locations:")
        for sku, loc in self.locations.items():
            print(f"    - {sku}: {loc}")
        print("=======================\n")


# ----------------------------- Workflow Engine ----------------------------- #

class OrderWorkflow:
    def __init__(self, ledger: RackLedger, auto: bool = False, delay: float = 0.0, decline: bool = False) -> None:
        self.ledger = ledger
        self.auto = auto
        self.delay = delay
        self.simulate_decline = decline

    def _wait_next(self, prompt: str = "Press Enter to move to the next step...") -> None:
        if self.auto:
            if self.delay > 0:
                time.sleep(self.delay)
        else:
            input(prompt)

    def _log(self, message: str) -> None:
        print(f"[{now_iso()}] {message}")

    def receive_order_and_locate_item(self, order: Order, target_rack: str) -> None:
        self._log(f"Order received: {order.order_id} for SKU={order.item.sku}. Locating item on rack...")
        order.item.location = STATION_WAREHOUSE_RACKS
        order.item.rack = target_rack
        self.ledger.add_item_to_rack(order.item.sku, target_rack)
        order.update_status(STATUS_ITEM_IN_PROCESS)
        self._log(f"Status -> {order.current_status} | Item located on rack {target_rack}")
        self.ledger.pretty_print()
        self._wait_next()

    def move_to_packing_station(self, order: Order) -> None:
        rack_id = order.item.rack or "UNKNOWN"
        self._log(f"Moving SKU={order.item.sku} from rack {rack_id} to packing station...")
        self.ledger.remove_item_from_rack(order.item.sku, rack_id=rack_id, new_location=STATION_PACKING)
        order.item.rack = None
        order.item.location = STATION_PACKING
        order.update_status(STATUS_READY_TO_PACK)
        self._log(f"Status -> {order.current_status} | Item at packing station.")
        self.ledger.pretty_print()
        self._wait_next()

    def label_package(self, order: Order, from_address: str, to_address: str) -> None:
        self._log("Labelling package (barcode, from/to)...")
        code = random_barcode(14)
        order.item.barcode = code
        order.label = ShippingLabel(from_address=from_address, to_address=to_address, barcode=code)
        order.update_status(STATUS_PACKAGE_LABELLED)
        self._log(f"Status -> {order.current_status} | Barcode={code}")
        self._wait_next()

    def sort_and_collate(self, order: Order, outbound_route: str) -> None:
        self._log(f"Sorting/collating SKU={order.item.sku} for outbound route '{outbound_route}'...")
        self.ledger.update_item_location(order.item.sku, STATION_SORTING)
        order.item.location = STATION_SORTING
        order.update_status(STATUS_READY_TO_BE_PICKED)
        self._log(f"Status -> {order.current_status} | Assigned route: {outbound_route}.")
        self.ledger.pretty_print()
        self._wait_next()

    def manager_approval(self, order: Order) -> bool:
        self.ledger.update_item_location(order.item.sku, STATION_AUDIT)
        order.item.location = STATION_AUDIT
        order.update_status(STATUS_AWAITING_APPROVAL)
        self._log(f"Status -> {order.current_status} | Awaiting Floor Manager decision (A=Approve, D=Decline).")

        decision = None
        if self.auto:
            decision = "D" if self.simulate_decline else "A"
            if self.delay > 0:
                time.sleep(self.delay)
        else:
            while decision not in ("A", "D"):
                decision = input("Floor Manager: Approve (A) or Decline (D)? ").strip().upper()

        if decision == "A":
            order.update_status(STATUS_APPROVAL_GRANTED)
            self._log(f"Manager decision: APPROVED. (Status -> {order.current_status})")
            return True
        else:
            order.update_status(STATUS_APPROVAL_DECLINED)
            self._log(f"Manager decision: DECLINED. (Status -> {order.current_status})")
            return False

    def load_to_truck(self, order: Order, truck_id: str) -> None:
        self._log(f"Routing SKU={order.item.sku} to truck loading dock for Truck {truck_id}...")
        self.ledger.update_item_location(order.item.sku, STATION_LOADING)
        order.item.location = STATION_LOADING
        order.update_status(STATUS_PACKAGE_LOADED)
        self._log(f"Status -> {order.current_status} | Process complete.")
        self.ledger.pretty_print()

    def run(self, order: Order, initial_rack: str, from_addr: str, to_addr: str,
            outbound_route: str, truck_id: str) -> None:
        self.receive_order_and_locate_item(order, target_rack=initial_rack)
        self.move_to_packing_station(order)
        self.label_package(order, from_address=from_addr, to_address=to_addr)
        self.sort_and_collate(order, outbound_route=outbound_route)

        approved = self.manager_approval(order)
        if not approved:
            self._log("Processing halted due to manager decline.")
            return

        self._wait_next()
        self.load_to_truck(order, truck_id=truck_id)


# ----------------------------- Demo / CLI ----------------------------- #

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warehouse Order Status Automation")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--decline", action="store_true")
    parser.add_argument("--no-csv", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    ledger = RackLedger(persist_csv=not args.no_csv)
    rack_ids = ["A1", "A2", "B1", "B2", "C3"]
    for r in rack_ids: ledger.register_rack(r)

    sku = "SKU-" + random_barcode(8)
    item = Item(sku=sku, description="Wireless Mouse, Black")
    order = Order(order_id="ORD-" + random_barcode(6), item=item)

    flow = OrderWorkflow(ledger, auto=args.auto, delay=args.delay, decline=args.decline)
    flow.run(order, random.choice(rack_ids), "Dallas TX", "Seattle WA", "SEA-07", "TRUCK-07")

    print("\n--- FINAL ORDER SUMMARY ---")
    print(f"Order ID  : {order.order_id} | Status: {order.current_status}")


if __name__ == "__main__":
    main()