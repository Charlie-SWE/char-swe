#kent state women's soccer roster

roster = [
    (0, "Emma Klein", "GK", "Junior"),
    ("00", "Jordan Levenhagen", "GK", "Freshman"),
    (1, "Leah Shaffer", "GK", "Senior"),
    (2, "Samantha Miller", "M", "Senior"),
    (3, "Zsofia Jakab", "F/M", "Freshman"),
    (4, "Alexa Muth", "Sophomore"),
    (5, "Katie Henahan", "M", "Junior"),
    (6, "Mia McLean Mercier", "D", "Freshman"),
    (7, "Kiyomi McCausland", "F", "Senior"),
    (8, "Clara Monck", "M", "Freshman"),
    (9, "Ava Todd", "D", "Senior"),
    (11, "Mary Mascaro", "F/M", "Freshman"),
    (12, "Jules Dolinski", "F", "Junior"),
    (13, "Allison Collins", "D", "Junior"),
    (14, "Allison Burkey", "D/M", "Senior"),
    (15, "Ciara Santiago", "F", "sophomore"),
    (16, "Abby Breitschuh", "D", "Graduate"),
    (17, "Lila Simon", "F", "Freshman"),
    (19, "Kelsey Salopek", "D", "Senior"),
    (20, "Ali Weibel", "D", "Junior"),
    (21, "Maya Justice", "M", "Sophomore"),
    (22, "Ava Lukyan", "M", "Junior"),
    (24, "Isabelle Leofanti", "F", "Sophomore"),
    (25, "Josie Morgan", "F", "Senior"),
    (27, "Mia Cleroux", "F", "Sophomore")

]

print("Kent State Women's Soccer Roster")
print("-" * 65)

print(f"{'No.':<6}{'Name':<25}{'Position':<12}{'Year'}")
print("-" * 65)

for number, name, position, year in roster:
    print(f"{str(number):<6}{name:<25}{position:<12}{year}")

    print("-" * 65)
    print("Total Players:", len(roster))