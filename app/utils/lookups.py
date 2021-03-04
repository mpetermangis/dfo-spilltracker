"""
This file defines lookup values for restricted text fields
"""

coord_types = ['Decimal Degrees', 'Degrees Decimal Minutes', 'Degrees Minutes Seconds']
poll_types = ['Unknown', 'Potential', 'Gasoline', 'Diesel', 'Heavy Oils (Bunker, Crude)', 'Other (Specify)']
quantity_units = ['gallons', 'litres', 'barrels', 'sheen dimensions - feet', 'sheen dimensions - meters', 'other']
roc_officers = ['Officer 1', 'Officer 2', 'Officer 3']
# timezones = [{'PST': 'America/Vancouver'}, {'MST': 'America/Edmonton'},
#              {'CST (Regina)':'America/Regina'}, {'CST (Winnipeg)': 'America/Winnipeg'},
#              {'EST': 'America/Toronto'}, {'AST': 'America/Halifax'},
#              {'Newfoundland': 'America/St_Johns'}]

timezones = [('PST', 'America/Vancouver'), ('MST', 'America/Edmonton'),
             ('CST (Regina)','America/Regina'), ('CST (Winnipeg)', 'America/Winnipeg'),
             ('EST', 'America/Toronto'), ('AST', 'America/Halifax'),
             ('Newfoundland', 'America/St_Johns')]

severity_levels = [1, 2, 3, 4, 5]

tz_reversed = {}
for display_tz, tz in timezones:
    tz_reversed[tz] = display_tz

lu = {'coord_types': coord_types,
      'poll_types': poll_types,
      'quantity_units': quantity_units,
      'timezones': timezones,
      'roc_officers': roc_officers,
      'severity_levels': severity_levels}
