# =====================================新版分车============================================================

import random

import logging


logging.basicConfig(
    filename='bus1_log.txt',  
    level=logging.INFO,       
    format='%(levelname)s - %(message)s' 
)

# vehicle_capacity = np.array([37,47])
# vehicle_costs = np.array([3200, 3800])  # 费用


AVERAGE = []
MIN_THRESHOLD = 2




def optimal_bus_combos(N, C_A, P_A, C_B, P_B, a_count=0, b_count=0, alpha=1.0, memo=None):
    if memo is None:
        memo = {}

    total_capacity = a_count * C_A + b_count * C_B
    if total_capacity >= N:
        total_cost = a_count * P_A + b_count * P_B
        total_vehicles = a_count + b_count
        
        max_cost = max(P_A, P_B) * (N // min(C_A, C_B)+1)  
        # max_vehicles = (N // min(C_A, C_B)) + (N // min(C_A, C_B))  
        normalized_cost = total_cost / max_cost
        # normalized_vehicles = total_vehicles / max_vehicles
        
        combined_cost = alpha * normalized_cost    # + (1 - alpha) * normalized_vehicles
        return (a_count, b_count), combined_cost 

    state = (a_count, b_count)
    if state in memo:
        return memo[state]

    best_combo = (0, 0)
    best_cost = float('inf')

    combo_a, cost_a = optimal_bus_combos(N, C_A, P_A, C_B, P_B, a_count + 1, b_count, alpha, memo)
    if cost_a < best_cost:
        best_cost = cost_a
        best_combo = combo_a

    combo_b, cost_b = optimal_bus_combos(N, C_A, P_A, C_B, P_B, a_count, b_count + 1, alpha, memo)
    if cost_b < best_cost:
        best_cost = cost_b
        best_combo = combo_b

    memo[state] = (best_combo, best_cost)
    return memo[state]

class Bus:

    empty_penalty = 0.8
    stop_penalty = 0.16

    def __init__(self, size, vehicle_capacity, vehicle_costs, init_reserved_seats=5):
        self.size = size
        self.capity = vehicle_capacity
        self.empty_seats = vehicle_capacity
        self.price = vehicle_costs

        self.reserved_seats = init_reserved_seats
        self.init_reserved_seats = init_reserved_seats

        self.pass_station = 0
        self.route = {}

    def __str__(self):
        return f"Bus type: {self.size}, Capacity: {self.capity}, Empty Seats: {self.empty_seats}, Price: {self.price}, Route: {self.route}, Pass Station: {self.pass_station}, Reserved Seats: {self.reserved_seats}"

    def calc_carrying_profit(self,passager_num):

        passager_num = passager_num if self.empty_seats > passager_num else self.empty_seats
        passager_num += self.reserved_seats
        pass_station = 0 if self.pass_station <= 0 else self.pass_station
        profit = passager_num/(self.capity + self.init_reserved_seats) * self.price - Bus.stop_penalty*self.price* pass_station
        if self.empty_seats == 0:
            profit = -float('inf')
        return profit
    
    def load_passenger(self,station_name,pnum):

        remain_passager = max(pnum - self.empty_seats, 0)
        self.empty_seats = max(self.empty_seats - pnum, 0)

        self.route.setdefault(station_name,0)
        self.route[station_name] += pnum - remain_passager
        self.pass_station = len(self.route)

        return remain_passager
    
    def remove_passenger(self,station_name,pnum=None):
        try:
            cur_pnum = self.route[station_name]
            if pnum is None or pnum >= cur_pnum:
                self.route.pop(station_name)
                self.pass_station = len(self.route)
                self.empty_seats += cur_pnum

            else:
                self.route[station_name] -= pnum
                self.empty_seats += pnum
            
        except Exception as e:
            logging.info(f"ERROR: remove_passenger error: {e}")
    
    def get_pnum_by_station(self,station_n):

        if station_n not in self.route:
            return 0
        else:
            return self.route[station_n]
        
    def sorted_route(self,reversed=False):

        self.route = dict(sorted(self.route.items(), key=lambda item: item[1]))
        return self.route
        
    def calc_seating_rate(self):
        rate = (self.init_reserved_seats + self.capity - self.empty_seats - self.reserved_seats)/(self.init_reserved_seats + self.capity)
        return rate

    def get_total_passenger_num(self):
        return self.capity - self.empty_seats + self.init_reserved_seats - self.reserved_seats

    def get_min_station(self):
        tmp_dict = sorted(self.route.items(), key=lambda x:x[1])
        return tmp_dict[0][0], tmp_dict[0][1]
    
    def get_max_station(self):
        tmp_dict = sorted(self.route.items(), key=lambda x:-x[1])
        return tmp_dict[0][0], tmp_dict[0][1]

def add_bus(combo,count=0):
    new_combo = None
    if combo[1] > count :
        new_combo = (combo[0]+count+1,combo[1]-count-1)
    else:
        new_combo = (combo[0],combo[1]+1)
    return new_combo

def plan_route_rough(larger_bus, small_bus,vehicle_capacity,vehicle_costs, stations,init_reserved_seats=1):
    bus_list = []
    sorted_stations = sorted(stations.items(), key=lambda x:-x[1])
    while True:
        is_opt = False
        for idx, station in enumerate(sorted_stations):
           
            if larger_bus > 0 and station[1] > 1.6*vehicle_capacity[1]:
                bus = Bus('Large', vehicle_capacity[1], vehicle_costs[1], init_reserved_seats)
                sorted_stations[idx] = (sorted_stations[idx][0],bus.load_passenger(station[0],station[1]))
                bus_list.append(bus)
                larger_bus -= 1
                is_opt = True
            elif small_bus >0 and station[1] > 1.6*vehicle_capacity[0]:
                bus = Bus('Small',vehicle_capacity[0], vehicle_costs[0], init_reserved_seats)
                sorted_stations[idx] = (sorted_stations[idx][0],bus.load_passenger(station[0],station[1]))
                bus_list.append(bus)
                small_bus -= 1
                is_opt = True

        if not is_opt:    
            break
    for l in range(larger_bus):
        bus_list.append(Bus('Large',vehicle_capacity[1], vehicle_costs[1], init_reserved_seats))
    for m in range(small_bus):
        bus_list.append(Bus('Small',vehicle_capacity[0], vehicle_costs[0], init_reserved_seats))

    sorted_stations = sorted(sorted_stations, key=lambda x:x[1])
    while True:
        for idx,station in enumerate(sorted_stations):
            if station[1] != 0:
                profits = [(bus.calc_carrying_profit(station[1]),index) for index, bus in enumerate(bus_list)]
                sorted_profits = sorted(profits,reverse=True)
                remain_passager = bus_list[sorted_profits[0][1]].load_passenger(*station)
                sorted_stations[idx] = (sorted_stations[idx][0],remain_passager)
        
        sorted_stations = sorted(sorted_stations, key=lambda x:-x[1])
        if sorted_stations[0][1] == 0:
            break
    return bus_list

def find_exchange_bus(bus_list,sta_name,pnum):
    ex_bus = []
    for bus in bus_list:
        if bus.get_pnum_by_station(sta_name) > max(6,pnum) :
            ex_bus.append(bus)
    if len(ex_bus):
        ex_bus = sorted(ex_bus, key=lambda x : len(x.route))
        return ex_bus[0]
    else:
        a = 99
    return None

def exchange_bus(opt_bus,ex_bus,min_station):
    if ex_bus is None:
        print("NONENEEEE!!!!")
        return None

    opt_sta, opt_max_pnum = opt_bus.get_max_station()
    ex_pnum = ex_bus.get_pnum_by_station(min_station)
    pnum = min(opt_max_pnum//2,ex_pnum//2)

    opt_bus.remove_passenger(opt_sta,pnum)
    ex_bus.remove_passenger(min_station,pnum)

    opt_bus.load_passenger(min_station,pnum)
    ex_bus.load_passenger(opt_sta,pnum)

def optimize_buses(bus_list):
    for optbus in bus_list:

        count = 0
        optbus.sorted_route()
        while len(optbus.route) > 3 and count < 3:
            min_station = list(optbus.route.keys())[count]
            min_passenger_count = optbus.route[min_station]
            count += 1

            for target_bus in bus_list:
                if len(target_bus.route) < 3 and target_bus is not optbus:
                    common_stations = set(optbus.route.keys()).intersection(set(target_bus.route.keys()) - {min_station})    
                    common_passenger_count = sum(target_bus.route[station] for station in common_stations)
                    if common_passenger_count >= min_passenger_count:
                        optbus.remove_passenger(min_station)
                        for station in common_stations:
                            transfer_count_to_optbus = min(target_bus.route[station], min_passenger_count)
                            target_bus.remove_passenger(station,transfer_count_to_optbus) 
                            target_bus.load_passenger(min_station,transfer_count_to_optbus)
                            optbus.load_passenger(station,transfer_count_to_optbus)
                            min_passenger_count -= transfer_count_to_optbus
                            if min_passenger_count == 0:
                                count = 0
                                break   
                        break
                elif target_bus is not optbus:
                    common_stations = set(optbus.route.keys()).intersection(set(target_bus.route.keys())) 
                    if len(common_stations) >= 2 and min_station in common_stations:
                        common_stations = common_stations - {min_station}
                        common_passenger_count = sum(target_bus.route[station] for station in common_stations)
                        if common_passenger_count >= min_passenger_count:
                            optbus.remove_passenger(min_station)
                            for station in common_stations:
                                transfer_count_to_optbus = min(target_bus.route[station], min_passenger_count)
                                target_bus.remove_passenger(station,transfer_count_to_optbus) 
                                target_bus.load_passenger(min_station,transfer_count_to_optbus)
                                optbus.load_passenger(station,transfer_count_to_optbus)
                                min_passenger_count -= transfer_count_to_optbus
                                if min_passenger_count == 0:
                                    count = 0
                                    break
                            break

    return bus_list

def plan_route_by_station(bus_list,reserved_seats=0):
    logging.info("^^^^^^^^^^^^^^^^^((((((plan_route_by_station))))))---------------")

    for opt_bus in bus_list:
        min_station, min_pnum = opt_bus.get_min_station()
        while min_pnum < MIN_THRESHOLD:
            ex_bus = find_exchange_bus(bus_list,min_station, min_pnum)
            exchange_bus(opt_bus,ex_bus,min_station)
            min_station, min_pnum = opt_bus.get_min_station()

    new_buses = optimize_buses(bus_list)
    for idx, bus in enumerate(new_buses):
        if len(bus.route) > 3:
            logging.info(f"*******WARNING bus route > 3********")
        logging.info(f"Bus : {bus.size}_{idx}, \nRoute: {bus.route.keys()}, Passengers: {bus.route.values()}")

    return new_buses
        
def plan_route(stations,vehicle_capacity,vehicle_costs,reserved_seats,best_combo):

    bus_list = plan_route_rough(*best_combo,vehicle_capacity,vehicle_costs,stations,init_reserved_seats = reserved_seats)
    for idx, bus in enumerate(bus_list):
        logging.info(f"Bus : {bus.size}_{idx} \n Route: {bus.route.keys()} Passengers: {bus.route.values()}")

    new_bus_list = plan_route_by_station(bus_list,reserved_seats)
    average_rate = 0
    for b in new_bus_list:
        average_rate += b.calc_seating_rate()
    logging.info(f"Average seating rate:{average_rate/len(new_bus_list)} ")

    return best_combo,new_bus_list

def check_route(stations, bus_list):

    total_passengers = {}
    bus_count = {}
    need_re_plan = False
    bus_station_count = {}

    for bus_index, bus in enumerate(bus_list):
        station_count = 0
        for station, passenger_count in bus.route.items():
            if passenger_count == 1:
                need_re_plan = True
            if station not in total_passengers:
                total_passengers[station] = 0
                bus_count[station] = 0
            total_passengers[station] += passenger_count
            bus_count[station] += 1  
            station_count += 1 

        bus_station_count[bus_index] = station_count
        if station_count > 3:
            need_re_plan = True

    for station, real_pnum in stations.items():
        if station in total_passengers:
            if total_passengers[station] != real_pnum:
                logging.info(f"Station '{station}' has {total_passengers[station]}, but requires {real_pnum}.")
        else:
            logging.info(f"Station '{station}' is missing from bus_list.")

    logging.info("\nBus counts per station:")
    for station, count in bus_count.items():
       logging.info(f"Station '{station}' is served by {count} buses.")
       if count > 4:
           need_re_plan = True

    return need_re_plan

def plan_route_top(total_sum,stations,vehicle_capacity,vehicle_costs):

    try:
        assert len(vehicle_capacity) == 2
        assert len(vehicle_costs) == 2
    except Exception as e:
        logging.info(f" ERROR: vehicle_capacity or vehicle_costs length is not 2")

    best_combo, best_cost = optimal_bus_combos(total_sum,
                                        vehicle_capacity[1],
                                        vehicle_costs[1],
                                        vehicle_capacity[0],
                                        vehicle_costs[0],alpha=1)
    
    best_cost = best_combo[0]*vehicle_costs[1] + best_combo[1]*vehicle_costs[0]

    cost = 0
    bus_list = None
    re_plan = False
    re_plan_count = 0
    add_combo = best_combo
    while True:
        if re_plan:
            logging.info(f"------------re_plan----------------------")
            add_combo = add_bus(best_combo,re_plan_count)
            re_plan_count += 1
        cost = add_combo[0]*vehicle_costs[1] + add_combo[1]*vehicle_costs[0]
        logging.info(f"Total Bus: {add_combo[0] + add_combo[1]} \
                Large Bus : {add_combo[0]}  \
                Small Bus : {add_combo[1]} \
                Total Cost: {cost}")

        com, bus_list = plan_route(stations,vehicle_capacity,vehicle_costs, 0, add_combo)
        re_plan = check_route(stations, bus_list)
        if not re_plan or re_plan_count > 4:
            break
    logging.info(f"XXXXXXX{cost - best_cost}*************************")
    return bus_list






# if __name__ == '__main__':
    # vehicle_capacity = np.array([37,47])
    # vehicle_costs = np.array([3200, 3800])

    # filename = 'stations2.json'
    # generate_weighted_data(500,12,filename)

    # stations_list, sums_list = load_data(filename)
    # for i, (stations, total_sum) in enumerate(zip(stations_list, sums_list)):
    #     logging.info(f"-----------------------------------------------")  
    #     logging.info(f"Dictionary {i + 1}: \n Total Passenger:{total_sum} \n {stations}")  
    #     best_combo, best_cost = optimal_bus_combos(total_sum,
    #                                         vehicle_capacity[1],
    #                                         vehicle_costs[1],
    #                                         vehicle_capacity[0],
    #                                         vehicle_costs[0],alpha=1)
        
    #     cost = best_combo[0]*vehicle_costs[1] + best_combo[1]*vehicle_costs[0]
    #     logging.info(f"*************BEST PRICE****************")
    #     logging.info(f"Total Bus: {best_combo[0] + best_combo[1]} \
    #             Large Bus : {best_combo[0]}  \
    #             Small Bus : {best_combo[1]} \
    #             Total Cost: {cost}")
        
        # plan_route_top(total_sum,stations,vehicle_capacity,vehicle_costs)
