
symbols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']


def char_swapping(plate):
    perms = []
    for x in range(0, len(plate)):
        for symbol in symbols:
            new_plate_string = ''
            plate_list = list(plate)
            plate_list[x] = symbol
            for char in plate_list:
                new_plate_string += char
            perms.append(new_plate_string)
    return perms


def less_one_char(plate):
    perms = []
    for x in range(0, len(plate)):
        new_plate_string = ''
        plate_list = list(plate)
        del plate_list[x]
        for char in plate_list:
            new_plate_string += char
        perms.append(new_plate_string)
    return perms


def add_one_char(plate):
    perms = []
    for x in range(0, len(plate)+1):
        for symbol in symbols:
            new_plate_string = ''
            plate_list = list(plate)
            plate_list.insert(x, symbol)
            for char in plate_list:
                new_plate_string += char
            perms.append(new_plate_string)
    return perms


def near_match(plate):
    permutations = char_swapping(plate)
    permutations += less_one_char(plate)
    if len(plate) < 7:
        permutations += add_one_char(plate)
    return permutations



