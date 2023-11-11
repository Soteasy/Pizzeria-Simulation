import datetime
import curses
import threading
import time
import random
from queue import Queue, Empty

orders_queue = Queue()
cook1_queue = Queue()
cook2_queue = Queue()
cook3_queue = Queue()
cook4_queue = Queue()
chef_queue = Queue()

class Worker(threading.Thread):
    def __init__(self, status_index, status):
        super().__init__()
        self.status_index = status_index
        self.status = status

    def pause(self, source_name):
        if random.random() < 0.20:
            pause_time = random.randint(10, 20)
            label = f"{source_name} Pause:".ljust(90)
            for t in range(pause_time):
                progress = int((t + 1) / pause_time * 100)
                self.status[self.status_index] = f"{label} [{'=' * (progress // 5)}{' ' * (20 - progress // 5)}] {progress}%"
                time.sleep(1)
            self.status[self.status_index] = f"{source_name} Back from pause. Waiting to start the work"

class Manager(Worker):
    def __init__(self, status_index, status):
        super().__init__(status_index, status)
        self.working = False

    def run(self):
        while True:
            while orders_queue.empty():
                time.sleep(1)
            order = orders_queue.get()
            self.working = True
            label = f"Manager:  Order {order} in progress".ljust(90)
            self.status[1] = f"Manager:  Order {order} in progress"
            processing_time = random.randint(15, 25)
            for t in range(processing_time):
                progress = int((t + 1) / processing_time * 100)
                self.status[1] = f"{label} [{'=' * (progress // 5)}{' ' * (20 - progress // 5)}] {progress}%"
                time.sleep(1)
            self.status[1] = f"Manager:  Order {order} processed"
            cook1_queue.put(order)
            cook2_queue.put(order)
            cook3_queue.put(order)
            cook4_queue.put(order)
            self.working = False
            self.pause("Manager: ")

class Cook(Worker):
    def __init__(self, name, cook_queue, status_index, status, chef_queue):
        super().__init__(status_index, status)
        self.name = name
        self.cook_queue = cook_queue
        self.chef_queue = chef_queue
        self.working = False

    def run(self):
        while True:
            self.status[self.status_index] = f"{self.name}:   Waiting to start the work."
            try:
                order = self.cook_queue.get(block=False)
            except Empty:
                time.sleep(1)
                continue
            cooking_time = random.randint(10, 40)
            self.working = True
            label = f"{self.name}:   Cooking order {order}:".ljust(90)
            for t in range(cooking_time):
                progress = int((t + 1) / cooking_time * 100)
                if progress < 10:
                    progress_str = f"{progress}%  "
                elif progress < 100:
                    progress_str = f"{progress}% "
                else:
                    progress_str = f"{progress}%"
                orders_list = f"Current orders: {list(self.cook_queue.queue)}"
                self.status[self.status_index] = f"{label} [{'=' * (progress // 5)}{' ' * (20 - progress // 5)}] {progress_str} {orders_list}"
                time.sleep(1)
            self.status[self.status_index] = f"{self.name}:   Cooking finished for order {order}"
            self.chef_queue.put(order)
            fixed_name = self.name + ":  "
            self.working = False
            self.pause(fixed_name)

class Chef(Worker):
    def __init__(self, chef_queue, status_index, status):
        super().__init__(status_index, status)
        self.chef_queue = chef_queue
        self.made_orders = []
        self.working = False

    def run(self):
        order_counts = {}
        while True:
            self.status[6] = f"Chef:     Waiting to start the work. Current orders: {order_counts}"
            while not self.chef_queue.empty():
                order = self.chef_queue.get()
                if order not in order_counts:
                    order_counts[order] = 0
                order_counts[order] += 1
                orders_list = f"Current orders: {order_counts}"
                self.status[6] = f"Chef:     Waiting to start the work. {orders_list}"

            # Find an order with at least 4 occurrences
            order_to_cook = None
            for order, count in order_counts.items():
                if count >= 4:
                    order_to_cook = order
                    break

            # If no such order is found, wait and then continue to the next iteration
            if order_to_cook is None:
                time.sleep(1)
                continue
            
            self.working = True
            del order_counts[order_to_cook]  # Delete the order from the dictionary
            cooking_time = random.randint(20, 30)
            label = f"Chef:     Preparing meal for order {order_to_cook}:".ljust(90)
            for t in range(cooking_time):
                progress = int((t + 1) / cooking_time * 100)
                if progress < 10:
                    progress_str = f"{progress}%  "
                elif progress < 100:
                    progress_str = f"{progress}% "
                else:
                    progress_str = f"{progress}%"

                while not self.chef_queue.empty():
                    order = self.chef_queue.get()
                    if order not in order_counts:
                        order_counts[order] = 0
                    order_counts[order] += 1
           
                orders_list = f"Current orders: {order_counts}"
                self.status[6] = f"{label} [{'=' * (progress // 5)}{' ' * (20 - progress // 5)}] {progress_str} {orders_list}"
                time.sleep(1)
            self.status[6] = f"Chef:     Meal prepared for order {order_to_cook}"
            self.made_orders.append(order_to_cook)
            self.status[7] = f"Made orders: {self.made_orders} -> {len(self.made_orders)}/10"
            if len(self.made_orders) == 10: 
                 Customer.stop_customers() 
            self.working = False
            self.pause("Chef:    ")

class Customer(threading.Thread):

    stop_event = threading.Event()
    made_orders = 0

    def __init__(self, status_index, status):
        super().__init__()
        self.status_index = status_index
        self.status = status
        self.orders = iter(random.sample(range(1, 1001), 30))

    def run(self):
         while True:
            if not Customer.stop_event.is_set():
                try:
                    order = next(self.orders)
                except StopIteration:
                    break
                orders_queue.put(order)
                Customer.made_orders += 1
                if not Customer.stop_event.is_set():
                    self.status[0] = f"Customer: Order {order} is placed. Total: {Customer.made_orders}. Current orders: {list(orders_queue.queue)} "
                else:
                    label = f"Customer: Order {order} is placed. Total: {Customer.made_orders}. Current orders: {list(orders_queue.queue)}".ljust(90)
                    self.status[0] = f"{label} CLOSED. FINISHING LAST ORDERS..."
                timer = 0
                wait_time = random.randint(10, 30)
                while timer < wait_time:
                    time.sleep(1)
                    timer += 1
                    label = f"Customer: Order {order} is placed. Total: {Customer.made_orders}. Current orders: {list(orders_queue.queue)}".ljust(90)
                    if Customer.stop_event.is_set(): 
                        self.status[0] = f"{label} CLOSED. FINISHING LAST ORDERS... "
                    else:
                        self.status[0] = f"{label} Time for next order: {timer}/{wait_time}s. "
            else:
                label = f"Customer: Order {order} is placed. Total: {Customer.made_orders}. Current orders: {list(orders_queue.queue)}".ljust(90)
                if orders_queue.empty():
                    label = f"Customer: Order {order} is placed. Total: {Customer.made_orders}. No orders left.".ljust(90)
                    self.status[0] = f"{label} FINISHED."
                self.status[0] = f"{label} CLOSED. FINISHING LAST ORDERS..."
                time.sleep(1)

    @classmethod
    def stop_customers(cls):
        cls.stop_event.set()
                
def main(stdscr):
    stdscr.clear()
    stdscr.nodelay(True)
    status = [""] * 9
    status[7] = "Made orders: [] -> 0/10"
    manager = Manager(1, status)
    manager.daemon = True
    manager.start()

    cook1 = Cook("Cook A", cook1_queue, 2, status, chef_queue)
    cook1.daemon = True
    cook1.start()

    cook2 = Cook("Cook B", cook2_queue, 3, status, chef_queue)
    cook2.daemon = True
    cook2.start()

    cook3 = Cook("Cook C", cook3_queue, 4, status, chef_queue)
    cook3.daemon = True
    cook3.start()

    cook4 = Cook("Cook D", cook4_queue, 5, status, chef_queue)
    cook4.daemon = True
    cook4.start()

    chef = Chef(chef_queue, 6, status)
    chef.daemon = True
    chef.start()

    customer = Customer(0, status)
    customer.daemon = True
    customer.start()

    start_time = datetime.datetime.now()

    simulation_ended = False

    try:
        while True:
    
            c = stdscr.getch()
            if c == ord('q'):
                break

            if not simulation_ended:
                сurrent_time = datetime.datetime.now()  # Текущее время
                elapsed_time = сurrent_time - start_time  # Прошедшее время
                formatted_time = str(elapsed_time).split(".")[0]
                status[8] = f"Simulation Timer: {formatted_time}. Press q to quit: "

            for i in range(9):
                stdscr.clrtoeol()
                stdscr.addstr(i, 0, status[i])

            if (orders_queue.empty() and
                  cook1_queue.empty() and
                  cook2_queue.empty() and
                  cook3_queue.empty() and
                  cook4_queue.empty() and
                  chef_queue.empty() and
                  manager.working == False and
                  cook1.working == False and
                  cook2.working == False and
                  cook3.working == False and
                  cook4.working == False and
                  chef.working == False and
                  Customer.stop_event.is_set()):
                    status[8] = f"Simulation Timer: {formatted_time}. Simulation ended. Press q to quit: "
                    stdscr.move(8, len(status[8]))
                    simulation_ended = True

            stdscr.refresh()
            time.sleep(1)

    finally:
        curses.endwin()
        print("Exit...")

if __name__ == "__main__":
    curses.wrapper(main)
