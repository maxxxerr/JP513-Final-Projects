from datetime import date, timedelta
from typing import List, Dict, Optional
import json


class UserCharacter:
    def __init__(self, username: str):
        self.username = username
        self.level = 1
        self.experience = 0
        self.skills: Dict[str, int] = {"Спорт": 1, "Интеллект": 1, "Быт": 1}

    def add_xp(self, amount: int, category: str) -> bool:
        self.experience += amount
        if category in self.skills:
            self.skills[category] += 1

        level_threshold = self.level * 100
        if self.experience >= level_threshold:
            self.level += 1
            return True
        return False

    def deduct_xp(self, amount: int) -> None:
        self.experience = max(0, self.experience - amount)

    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "level": self.level,
            "experience": self.experience,
            "skills": self.skills,
        }


class Habit:
    def __init__(
        self,
        title: str,
        description: str,
        category: str,
        schedule_type: str,
        schedule_days: Optional[List[int]] = None, 
        creation_date: Optional[date] = None,
    ):
        self.title = title
        self.description = description
        self.category = category
        self.schedule_type = schedule_type
        self.schedule_days = schedule_days if schedule_days is not None else []
        self.creation_date = creation_date or date.today()
        self.dates_completed: List[date] = []
        self.current_streak = 0
        self.max_streak = 0

    @staticmethod
    def _is_date_in_custom_schedule(target_date: date, schedule_days: List[int]) -> bool:
        return target_date.weekday() in schedule_days

    @staticmethod
    def _get_last_scheduled_day_before(today: date, habit: "Habit") -> Optional[date]:

        if habit.schedule_type == "everyday":
            return today - timedelta(days=1)

        check_date = today - timedelta(days=1)
        while check_date >= habit.creation_date:
            if Habit._is_date_in_custom_schedule(check_date, habit.schedule_days):
                return check_date
            check_date -= timedelta(days=1)
        return None

    def check_in(self, target_date: Optional[date] = None) -> Dict:
        target_date = target_date or date.today()

        if self.schedule_type == "custom":
            if not self._is_date_in_custom_schedule(target_date, self.schedule_days):
                return {
                    "success": False,
                    "reason": "День не входит в расписание привычки",
                    "date": target_date.isoformat(),
                }

        if target_date in self.dates_completed:
            return {
                "success": False,
                "reason": "Отметка на эту дату уже есть",
                "date": target_date.isoformat(),
            }

        self.dates_completed.append(target_date)
        self.dates_completed.sort()

        self._recalculate_streak(target_date)

        new_record = False
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
            new_record = True

        return {
            "success": True,
            "date": target_date.isoformat(),
            "current_streak": self.current_streak,
            "max_streak": self.max_streak,
            "new_record": new_record,
        }

    def _recalculate_streak(self, reference_date: date) -> None:
        self.current_streak = 0
        check_date = reference_date

        while True:
            if self.schedule_type == "custom":
                if not self._is_date_in_custom_schedule(check_date, self.schedule_days):
                    check_date -= timedelta(days=1)
                    continue
            if check_date in self.dates_completed:
                self.current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "schedule_type": self.schedule_type,
            "schedule_days": self.schedule_days,
            "creation_date": self.creation_date.isoformat(),
            "dates_completed": [d.isoformat() for d in self.dates_completed],
            "current_streak": self.current_streak,
            "max_streak": self.max_streak,
        }




class HabitManager:
    def __init__(self, user: UserCharacter):
        self.user = user
        self.habits: List[Habit] = []

    def add_habit(
        self,
        title: input("название:"),
        description: input("описание:"),
        category: input("катигория:"),
        schedule_type: input("тип расписания:"),
        schedule_days: Optional[List[int]] = None,
    ) -> Habit:
        habit = Habit(
            title=title,
            description=description,
            category=category,
            schedule_type=schedule_type,
            schedule_days=schedule_days or [],
        )
        self.habits.append(habit)
        return habit

    def delete_habit(self, title: str) -> bool:
        for i, h in enumerate(self.habits):
            if h.title == title:
                del self.habits[i]
                return True
        return False

    def complete_habit(self, title: str) -> Dict:
        habit = next((h for h in self.habits if h.title == title), None)
        if not habit:
            return {"success": False, "reason": "Привычка не найдена"}

        result = habit.check_in()
        if not result["success"]:
            return result

        base_xp = 20
        streak_bonus = habit.current_streak * 2
        total_xp = base_xp + streak_bonus

        level_up = self.user.add_xp(total_xp, habit.category)

        return {
            "success": True,
            "habit_title": habit.title,
            "xp_gained": total_xp,
            "current_streak": habit.current_streak,
            "max_streak": habit.max_streak,
            "new_record": result["new_record"],
            "level_up": level_up,
        }

    def update_streaks_and_penalties(self) -> List[str]:
        logs: List[str] = []
        today = date.today()

        for habit in self.habits:
            last_scheduled = Habit._get_last_scheduled_day_before(today, habit)
            if last_scheduled is None:
                continue

            if last_scheduled not in habit.dates_completed:
                habit.current_streak = 0
                self.user.deduct_xp(15)
                day_name = last_scheduled.strftime("%A")
                log_msg = (
                    f"Привычка [{habit.title}] прервана! "
                    f"Расчетный день ({day_name}) был пропущен. Страйк сброшен!"
                )
                logs.append(log_msg)

        return logs

    def get_habit_by_title(self, title: str) -> Optional[Habit]:
        return next((h for h in self.habits if h.title == title), None)

    def to_dict(self) -> Dict:
        return {
            "user": self.user.to_dict(),
            "habits": [h.to_dict() for h in self.habits],
        }


def generate_7_day_progress_grid(manager: HabitManager) -> str:
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    lines = []
    header = " | ".join(d.strftime("%d.%m (%a)") for d in dates)
    lines.append("Дата: " + header)
    lines.append("-" * len(header))

    for habit in manager.habits:
        row = []
        for d in dates:
            if habit.schedule_type == "custom":
                if not Habit._is_date_in_custom_schedule(d, habit.schedule_days):
                    row.append("-")
                    continue
            marker = "[x]" if d in habit.dates_completed else "[ ]"
            row.append(marker)
        lines.append(f"{habit.title}: " + " ".join(row))

    return "\n".join(lines)


if __name__ == "__main__":
    user = UserCharacter(input("имя:"))
    manager = HabitManager(user)

    manager.add_habit
    manager.add_habit

    manager.complete_habit("Утренняя зарядка")
    manager.complete_habit("Чтение книги")

    logs = manager.update_streaks_and_penalties()
    if logs:
        print("Нарушения:")
        for log in logs:
            print(log)

    print("\nПрогресс за 7 дней:")
    print(generate_7_day_progress_grid(manager))

    data = manager.to_dict()
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print(json_str)