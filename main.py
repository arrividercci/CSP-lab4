import csv
import math
import random

groups = {
    'Group1': [30, ['п/г1', 'п/г2']],
    'Group2': [30, ['п/г1', 'п/г2']]
}
subjects = {
    'Group1': [
        ('Subject1', 10, 'Lecture', False),
    ],
    'Group2': [
        ('Subject2',10, 'Lecture', False)
    ]
}
teachers = {
    'T1': [
        ('Subject1', 'Lecture'),
        ('Subject2', 'Lecture')
    ]
}
auditoriums = {
    'Room1': 60
}

slots = [(day, hour) for day in range(1, 6) for hour in range(1, 5)]

class Variable:
    def __init__(self, id, subject, lesson_type, group, subgroup=None):
        self.id = id
        self.subject = subject
        self.type = lesson_type
        self.group = group
        self.subgroup = subgroup

def generate_variables(groups, subjects):
    lessons = []
    lesson_id = 0
    for group, subject_data in subjects.items():
        if group not in groups:
            continue
        for subject_name, subject_num, subject_type, requires_subgroups in subject_data:
            if subject_type == 'Lecture':
                for _ in range(subject_num):
                    lessons.append(Variable(lesson_id, subject_name, 'Lecture', group))
                    lesson_id += 1

            if subject_type == 'Practice':
                if requires_subgroups:
                    num_per_subgroup = math.ceil(subject_num / len(groups[group][1]))
                    for subgroup in groups[group][1]:
                        for _ in range(num_per_subgroup):
                            lessons.append(Variable(lesson_id, subject_name, 'Practice', group, subgroup))
                            lesson_id += 1
                else:
                    for _ in range(subject_num):
                        lessons.append(Variable(lesson_id, subject_name, 'Practice', group))
                        lesson_id += 1
    return lessons

def generate_domains(lessons, teachers, rooms, groups):
    domains = {}
    for lesson in lessons:
        possible_values = []
        possible_teachers = [teacher for teacher, teacher_subjects in teachers.items() if any(subject == (lesson.subject, lesson.type) for subject in teacher_subjects)]
        if not possible_teachers:
            continue

        group_size = groups[lesson.group][0]

        if lesson.subgroup:
            group_size = math.ceil(group_size / len(groups[lesson.group][1]))

        possible_rooms = [room for room, capacity in auditoriums.items() if capacity >= group_size]

        if not possible_rooms:
            continue

        for day, period in slots:
            for room in possible_rooms:
                for teacher in possible_teachers:
                    possible_values.append((day, period, room, teacher))
        domains[lesson.id] = possible_values

    return domains

variables = generate_variables(groups, subjects)

domains = generate_domains(variables, teachers, auditoriums, groups)

class CSP:
    def __init__(self, variables, domains, teachers, rooms, groups):
        self.variables = variables
        self.domains = domains
        self.lecturers = teachers
        self.auditoriums = rooms
        self.groups = groups

    def is_consistent(self, assignment, var, value):
        day, pair, room, teacher = value
        for other_var_id, other_value in assignment.items():
            other_day, other_pair, other_room, other_teacher = other_value
            if day == other_day and pair == other_pair:
                if room == other_room:
                    return False
                if teacher == other_teacher:
                    return False
                if self.variables[var].group == self.variables[other_var_id].group:
                    if self.variables[var].subgroup and self.variables[other_var_id].subgroup:
                        if self.variables[var].subgroup == self.variables[other_var_id].subgroup:
                            return False
                    else:
                        return False

        group_size = groups[self.variables[var].group][0]
        if self.variables[var].subgroup and self.variables[var].group.subgroups:
            group_size = math.ceil(group_size / len(groups[self.variables[var].group][1]))

        possible_rooms = [a for a, capacity in auditoriums.items() if capacity >= group_size]

        if not possible_rooms:
            return False
        return True

    def unassigned_variable(self, assignment):
        # Використовуємо MRV евристику
        unassigned_vars = [v for v in self.variables if v.id not in assignment]
        # MRV
        min_domain_size = min(len(self.domains[v.id]) for v in unassigned_vars)
        mrv_vars = [v for v in unassigned_vars if len(self.domains[v.id]) == min_domain_size]
        if len(mrv_vars) == 1:
            return mrv_vars[0]
        # Ступенева евристика (degree)
        max_degree = -1
        selected_var = None
        for var in mrv_vars:
            degree = 0
            for other_var in self.variables:
                if other_var.id != var.id and self.are_neighbors(var, other_var):
                    degree += 1
            if degree > max_degree:
                max_degree = degree
                selected_var = var
        return selected_var

    def are_neighbors(self, first_var, second_var):
        if first_var.group == second_var.group:
            return True
        share_lecturers = set(var1.subject for var1 in self.variables if var1.subject in second_var.subject)
        if share_lecturers:
            return True
        return False

    def order_domains(self, var, assignment):
        # Впорядковуємо домен за LCV (Least Constraining Value)
        def count_conflicts(value):
            day, period, aud, teacher = value
            conflicts = 0
            for other_var in self.variables:
                if other_var.id in assignment:
                    continue
                for other_value in self.domains[other_var.id]:
                    other_day, other_period, other_aud, other_teacher = other_value
                    if day == other_day and period == other_period:
                        if aud == other_aud or teacher == other_teacher:
                            conflicts += 1
                        if var.group == other_var.group:
                            conflicts += 1
            return conflicts

        return sorted(self.domains[var.id], key=lambda value: count_conflicts(value))

    def backtrack(self, assignment):

        if len(assignment) == len(self.variables):
            return assignment

        var = self.unassigned_variable(assignment)

        # Впорядкування значень за LCV
        ordered_values = self.order_domains(var, assignment)

        for value in ordered_values:
            if self.is_consistent(assignment, var.id, value):
                assignment[var.id] = value
                result = self.backtrack(assignment)
                if result:
                    return result
                del assignment[var.id]
        return None

    def find_solution(self):
        return self.backtrack({})

csp = CSP(variables, domains, teachers, auditoriums, groups)

solution = csp.find_solution()

if not solution:
    print("Не вдалося знайти розклад, який задовольняє всі жорсткі обмеження.")
else:
    for id, (day, period, room, teacher) in solution.items():
        lesson = next((s for s in variables if s.id == id), None)
        if not lesson:
            continue
        print(f"Group: {lesson.group}, Day {day}, Pair {period}: Subject {lesson.subject}, Teacher {teacher}, Room {room}, Type: {lesson.type}")

