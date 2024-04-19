#!/usr/bin/python3

# simple function that writes out a dictionary into csv files
# right now only used for austrian ranking calculator

import csv

def write_austrian_ranking_csv(austrian_ranking,csv_file_path):
    with open(csv_file_path+'.csv', mode = 'w') as csv_file:
        fieldnames = ['name', 'aut_sum', 'foreign_sum', 'sum']
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore',delimiter=',')

        csv_writer.writeheader()
        for x in austrian_ranking:
            if x['sum']>0:
                csv_writer.writerow(x)

    with open(csv_file_path+'_detailed.csv', mode = 'w') as csv_file:
        fieldnames = ['name', 'aut_sum', 'foreign_sum', 'sum','aut_tourneys','foreign_sorted']
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore',delimiter=',')

        csv_writer.writeheader()
        for x in austrian_ranking:
            if x['sum']>0:
                csv_writer.writerow(x)



