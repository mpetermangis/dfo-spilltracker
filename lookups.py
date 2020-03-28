"""
This file defines lookup values for restricted text fields
"""

coord_types = ['Decimal Degrees', 'Degrees Decimal Minutes', 'Degrees Minutes Seconds']
poll_types = ['Unknown', 'Potential', 'Gasoline', 'Diesel', 'Heavy Oils (Bunker, Crude)', 'Other (Specify)', 'custom']
quantity_units = ['gallons', 'litres', 'barrels', 'sheen dimensions - feet', 'sheen dimensions - meters', 'other']
roc_officers = ['Officer 1', 'Officer 2', 'Officer 3']
timezones = ['America/Vancouver', 'America/Edmonton', 'America/Regina',
             'America/Winnipeg', 'America/Toronto', 'America/Halifax', 'America/St_Johns']

lu = {'coord_types': coord_types,
      'poll_types': poll_types,
      'quantity_units': quantity_units,
      'timezones': timezones,
      'roc_officers': roc_officers}
