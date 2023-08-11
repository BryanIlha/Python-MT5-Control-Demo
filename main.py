import customtkinter as ctk
import MetaTrader5 as mt5
import pandas as pd
import configparser
from datetime import datetime
from tkinter import messagebox
from tkinter import ttk
import time
import schedule
import threading


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class ControlApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap('icon.ico')
        self.geometry(f"{210}x{370}")
        self.resizable(False, False)
        self.heading_window = None
        self.title("Control")
        self.attributes('-topmost', True)
        self.full_mode()


    def full_mode(self):
        self.clear_tab()
        self.counter_box = 0
        
        self.brokerage_switch = ctk.CTkSegmentedButton(self, values=["Brokerage A", "Brokerage B"],
                                                       command=self.get_data_outschedule)
        self.brokerage_switch.set('Brokerage B')
        self.brokerage_switch.configure(selected_color='green')
        self.brokerage_switch.pack()
        
        self.client_lbl = ctk.CTkLabel(self, text=f"Client: ",
                                         text_color="black", bg_color="gold", width=200,)
        self.client_lbl.pack()

        self.initial_blce_lbl = ctk.CTkLabel(self, text="Initial Balance: 0",
                                                  width=200, bg_color='#666666')
        self.initial_blce_lbl.pack()

        self.total_pft_lbl = ctk.CTkLabel(self, text="Total Profit: 0",
                                               width=200, bg_color='#666666')
        self.total_pft_lbl.pack()

        self.open_pft_lbl = ctk.CTkLabel(self, text="Open Profit: 0",
                                              width=200, bg_color='#666666')
        self.open_pft_lbl.pack()

        self.closed_pft_lbl = ctk.CTkLabel(self, text="Closed Profit: 0",
                                                width=200, bg_color='#666666')
        self.closed_pft_lbl.pack()

        self.opt_lbl = ctk.CTkLabel(self, text="volume: 0",
                                       width=200, bg_color='#666666')
        self.opt_lbl.pack()

        self.percent_btn = ctk.CTkButton(self, text="Percentage: 0%", width=200,
                                            hover_color='gold', command=self.box_mode)        
        self.percent_btn.pack()

        self.window_heading = ctk.CTkButton(self, text='Open Trades', command=self.open_toplevel)
        self.window_heading.pack(pady=10)

        self.get_data_outschedule('empty')
        self.counter_color = 0
        self.counter_schedule = False

        schedule.every().day.at("00:01").do(self.update_initial_balance) 
        self.schedule_thread = threading.Thread(target=self.run_schedule)
        self.schedule_thread.start()  

        self.update_lbls()   

    def box_mode(self):
        self.clear_tab()
        self.geometry(f'{200}x{100}')

        font_size = 25  

        self.box_btn = ctk.CTkButton(self, text="0%", width=100, height=100,
                                     hover_color='gold', command=self.full_mode)
        self.box_btn.configure(font=("Helvetica", font_size))
        self.box_btn.pack(side=ctk.LEFT)  

        self.reset_btn = ctk.CTkButton(self, text='Reset', fg_color='grey',
                                       width=100, height=100, hover_color='gold',
                                       command=self.reset_profit)
        self.reset_btn.configure(font=("Helvetica", font_size))
        self.reset_btn.pack(side=ctk.LEFT)

        self.counter_box = 1

    def reset_profit(self):
        self.initial_balance = float(mt5.account_info().equity)

    def update_initial_balance(self):
        print('balance reset')
        self.initial_balance = float(mt5.account_info().equity)
        now = datetime.now()
        self.from_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.to_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    def run_schedule(self):   
        while True:
            schedule.run_pending()
            time.sleep(1)

    def on_closing(self):
        self.after_cancel(self.after_id)  
        self.destroy()

    def initialize_mt5(self, switch_brokerage):
        config = configparser.ConfigParser()

        config.read('config.ini')
        
        if switch_brokerage == "Brokerage B":
            brokerage_path = config.get('brokerages', 'Brokerage B')
        else:
            brokerage_path = config.get('brokerages', 'Brokerage A')
        
        if not mt5.initialize(brokerage_path):
            messagebox.showerror(title="Error",
                                 message=f"Error opening {switch_brokerage}", 
                                 icon="cancel")
            quit()

    def get_multiplier(self, brokerage): 
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        if brokerage == 'Brokerage B':
            multipliers = dict(config['multiplier_brokerage_b'])
        elif brokerage == 'Brokerage A':
            multipliers = dict(config['multiplier_brokerage_a'])
        
        multipliers = {symbol: float(multiplier) for symbol, multiplier in multipliers.items()}
        return multipliers

    def clear_tab(self):
        for widget in self.winfo_children():
            widget.pack_forget()

    def get_closed_deals(self, column):
        if self.df_deals is not None:
            closed_value = round(self.df_deals[column].iloc[0:].sum(), 2)
        else:
            closed_value = 0
        return closed_value

    def get_deal_df(self):
        try:
            deals = mt5.history_deals_get(self.from_date, self.to_date)
            df_deals = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
            df_deals = df_deals[df_deals['entry'] != 0]
            df_deals['symbol'] = df_deals['symbol'].str.replace('#', '')
            df_deals['symbol'] = df_deals['symbol'].str.lower()

            self.df_deals = df_deals
        except:
            self.df_deals = None

    def get_commission(self, brokerage):
        if self.df_deals is not None:
            df_volume_volume = self.df_deals.groupby('symbol')['volume'].sum().reset_index()

            multipliers = self.get_multiplier(brokerage)
            
            df_volume_volume['multiplier'] = df_volume_volume['symbol'].map(multipliers)
            df_volume_volume['multiplier'].fillna(0, inplace=True)
            df_volume_volume['commission'] = df_volume_volume['volume'] * df_volume_volume['multiplier']
            commission_value = round(df_volume_volume['commission'].iloc[0:].sum(), 2)
        else:
            commission_value = 0
        
        return commission_value

    def get_open_deals(self, column):
        positions = mt5.positions_get()
        if len(positions) == 0:
            open_value = 0
        else:
            df_positions = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
            df_positions['time'] = pd.to_datetime(df_positions['time'], unit='s')
            today = datetime.now().date()
            df_positions = df_positions.loc[df_positions['time'].dt.date == today]
            open_value = round(df_positions[column].iloc[0:].sum(), 2)
            
        return open_value

    def get_data_outschedule(self, values):
        self.received_path = self.brokerage_switch.get()
        self.initialize_mt5(self.received_path)

        now = datetime.now()
        self.from_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.to_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        self.get_deal_df()

        closed_profit = float(self.get_closed_deals('profit'))
        open_profit = float(self.get_open_deals('profit'))
        total_profit = closed_profit + open_profit
              
        current_balance = float(mt5.account_info().equity)
                
        self.initial_balance = current_balance - total_profit

    def get_values(self):
        self.client_login = str(mt5.account_info().login)
        self.closed_profit = float(self.get_closed_deals('profit'))
        self.open_profit = float(self.get_open_deals('profit'))
        self.total_profit = self.closed_profit + self.open_profit
        self.current_balance = float(mt5.account_info().equity)
        self.total_profit = self.current_balance - self.initial_balance
                    
        self.current_percentage = round((self.total_profit / self.initial_balance) * 100, 2)
                    
        self.commission_volume = self.get_commission(self.received_path)

    def open_trades(self):
        if self.open_profit != 0:
            self.window_heading.configure(text='Open Trades', fg_color='red')
            self.geometry(f"{210}x{270}")
                        
            if self.counter_color == 2:
                self.window_heading.configure(fg_color='grey')
                self.counter_color = 0
                self.counter_color += 1
        else:
            self.geometry(f"{210}x{230}")  

    def define_percentage_color(self):
        if self.current_percentage < 0:
            self.percent_btn.configure(fg_color='red')
        elif self.current_percentage > 0:
            self.percent_btn.configure(fg_color='green')
        else:
            self.percent_btn.configure(fg_color='grey')

    def update_lbls(self):
        if self.winfo_exists():
            self.get_deal_df()
            self.get_values()

            if self.counter_box == 1:
                self.box_btn.configure(text=f'{self.current_percentage} %')
                if self.current_percentage < 0:
                    self.box_btn.configure(fg_color='red')
                elif self.current_percentage > 0:
                    self.box_btn.configure(fg_color='green')
                else:
                    self.box_btn.configure(fg_color='grey')
            if self.counter_box == 0:
                self.client_lbl.configure(text=f'{self.client_login}')
                self.initial_blce_lbl.configure(text=f"Initial Balance: {self.initial_balance:.2f} USD")
                self.total_pft_lbl.configure(text=f"Total Profit: {self.total_profit:.2f} USD")
                self.open_pft_lbl.configure(text=f"Open Profit: {self.open_profit:.2f} USD")
                self.closed_pft_lbl.configure(text=f"Closed Profit: {self.closed_profit:.2f} USD")
                self.opt_lbl.configure(text=f'Operational = {self.commission_volume}')
                self.percent_btn.configure(text=f'Percentage = {self.current_percentage}%')

                self.open_trades()
                self.define_percentage_color()                   
                
            self.after_id = self.after(500, self.update_lbls)

    def open_toplevel(self):
        if self.heading_window is None or not self.heading_window.winfo_exists():
            self.heading_window = Table(self)  
        else:
            self.heading_window.focus()


class Table(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.after(250, lambda: self.iconbitmap('icon.ico'))        
        self.geometry("300x200")
        self.resizable(False, False)
        self.title("Table") 

        self.title_lbl = ctk.CTkLabel(self, text='Open Trades',
                                        text_color="black", bg_color="gold", width=300)  
        self.title_lbl.pack()

        self.table = ttk.Treeview(self, columns=('Symbol', 'Volume', 'Type', 'Profit'),
                                  show='headings')
        self.table.heading('Symbol', text='Symbol')
        self.table.heading('Volume', text='Volume')
        self.table.heading('Type', text='Type')
        self.table.heading('Profit', text='Profit')
        self.table.column('Symbol', width=75)
        self.table.column('Volume', width=75)
        self.table.column('Type', width=75)
        self.table.column('Profit', width=75)
        self.table.pack()
        self.table.tag_configure('bg', background='grey')  
        self.table.tag_configure('fg', foreground='black')

        self.operational_table()

    def get_position_df(self):
        positions = mt5.positions_get()

        if len(positions) > 0:
            df_positions = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
            df_positions['time'] = pd.to_datetime(df_positions['time'], unit='s')
           
   
            df_positions['type'] = df_positions['type'].map({0: 'BUY', 1: 'SELL'})
            df_positions['symbol'] = df_positions['symbol'].str.replace('#', '')
            df_positions['symbol'] = df_positions['symbol'].str.cat([' '] * len(df_positions), sep='')

            self.df_positions = df_positions
        else:
            self.df_positions = None
    
    def operational_table(self):
        self.table.delete(*self.table.get_children())

        self.get_position_df()

        operations_list = []
        if self.df_positions is not None: 
            for _, row in self.df_positions.iterrows():
                symbol = row['symbol']
                volume = row['volume']
                deal_type = row['type']
                profit = row['profit']
                    
                operations_list.append([symbol, volume, deal_type, profit])

            if len(operations_list) > 0:
                for operation in operations_list:
                    self.table.insert('', 'end', values=operation, tags=('bg', 'fg'))
        else:
            self.withdraw()
        
        self.after_id = self.after(500, self.operational_table)


if __name__ == "__main__":
    app = ControlApp()
    app.mainloop()
