"""
Умный конфигуратор и калькулятор кредита/лизинга с предодобрением
Версия 1.0 для компании "Евроальянс"
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import re

# ==================== МОДЕЛЬ ДАННЫХ ====================

@dataclass
class ClientData:
    """Конфиденциальные данные клиента"""
    full_name: str
    birth_date: str
    passport_series: str
    passport_number: str
    phone: str
    email: str
    monthly_income: float
    employment_type: str  # 'employed', 'self_employed', 'business_owner'
    experience_months: int
    
    def validate(self) -> Tuple[bool, str]:
        """Валидация введенных данных"""
        if not re.match(r'^[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+$', self.full_name):
            return False, "ФИО должно быть в формате: Фамилия Имя Отчество"
        
        if not re.match(r'^\d{4}\s\d{6}$', f"{self.passport_series} {self.passport_number}"):
            return False, "Паспорт должен быть в формате: 1234 567890"
            
        if self.monthly_income < 15000:
            return False, "Доход должен быть не менее 15000 руб."
            
        return True, "Данные валидны"
    
    def get_hash(self) -> str:
        """Хеширование персональных данных для безопасности"""
        data_string = f"{self.passport_series}{self.passport_number}{self.birth_date}"
        return hashlib.sha256(data_string.encode()).hexdigest()[:16]

@dataclass
class Vehicle:
    """Данные об автомобиле"""
    brand: str
    model: str
    year: int
    price: float
    vin: str
    category: str  # 'new', 'used'
    
    def get_residual_value(self, months: int) -> float:
        """Расчет остаточной стоимости для лизинга"""
        if self.category == 'new':
            # Новая машина теряет 20% в первый год, потом 10% в год
            years = months / 12
            if years <= 1:
                return self.price * 0.80
            else:
                return self.price * (0.80 - (years - 1) * 0.10)
        else:
            # Б/у машина теряет 15% в год
            years = months / 12
            return self.price * (1 - years * 0.15)

@dataclass
class CalculationParameters:
    """Параметры расчета"""
    financing_type: str  # 'credit' или 'leasing'
    amount: float
    initial_payment: float
    months: int
    vehicle: Optional[Vehicle] = None
    insurance_included: bool = True
    life_insurance: bool = False
    
    @property
    def financed_amount(self) -> float:
        return self.amount - self.initial_payment

@dataclass
class CalculationResult:
    """Результаты расчета"""
    monthly_payment: float
    total_payment: float
    overpayment: float
    effective_rate: float
    schedule: List[Dict]
    approval_status: str
    approval_probability: float
    conditions: Dict
    calculation_id: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

# ==================== БАЗОВЫЕ КЛАССЫ ====================

class BaseCalculator(ABC):
    """Абстрактный класс калькулятора"""
    
    @abstractmethod
    def calculate(self, params: CalculationParameters) -> CalculationResult:
        pass
    
    @abstractmethod
    def validate_parameters(self, params: CalculationParameters) -> Tuple[bool, str]:
        pass

class BaseScoringEngine(ABC):
    """Абстрактный класс скоринговой системы"""
    
    @abstractmethod
    def assess_client(self, client: ClientData, params: CalculationParameters) -> Tuple[float, str]:
        pass

# ==================== РЕАЛИЗАЦИЯ КАЛЬКУЛЯТОРА ====================

class SmartCalculator(BaseCalculator):
    """Умный калькулятор с поддержкой кредита и лизинга"""
    
    def __init__(self):
        self.base_rates = {
            'credit': {'new': 0.159, 'used': 0.189},
            'leasing': {'new': 0.149, 'used': 0.179}
        }
        
    def validate_parameters(self, params: CalculationParameters) -> Tuple[bool, str]:
        """Валидация параметров расчета"""
        
        if params.amount <= 0:
            return False, "Сумма должна быть положительной"
        
        if params.initial_payment < params.amount * 0.15:
            return False, "Первоначальный взнос не менее 15%"
            
        if params.months < 12 or params.months > 84:
            return False, "Срок должен быть от 12 до 84 месяцев"
            
        if params.financing_type not in ['credit', 'leasing']:
            return False, "Тип финансирования должен быть 'credit' или 'leasing'"
            
        return True, "Параметры валидны"
    
    def calculate_annuity_payment(self, amount: float, annual_rate: float, months: int) -> float:
        """Расчет аннуитетного платежа"""
        monthly_rate = annual_rate / 12
        coefficient = (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        return amount * coefficient
    
    def calculate_effective_rate(self, params: CalculationParameters, monthly_payment: float) -> float:
        """Расчет эффективной процентной ставки (упрощенный)"""
        total_cost = monthly_payment * params.months
        return ((total_cost / params.financed_amount) - 1) * (12 / params.months) * 100
    
    def generate_schedule(self, params: CalculationParameters, monthly_payment: float, annual_rate: float) -> List[Dict]:
        """Генерация графика платежей"""
        schedule = []
        balance = params.financed_amount
        monthly_rate = annual_rate / 12
        current_date = datetime.now()
        
        for month in range(1, params.months + 1):
            interest = balance * monthly_rate
            principal = monthly_payment - interest
            balance -= principal
            
            schedule.append({
                'month': month,
                'date': (current_date + timedelta(days=30*month)).strftime('%d.%m.%Y'),
                'payment': round(monthly_payment, 2),
                'principal': round(principal, 2),
                'interest': round(interest, 2),
                'balance': max(0, round(balance, 2))
            })
        
        return schedule
    
    def calculate(self, params: CalculationParameters) -> CalculationResult:
        """Основной метод расчета"""
        
        # Определяем базовую ставку
        vehicle_type = params.vehicle.category if params.vehicle else 'used'
        base_rate = self.base_rates[params.financing_type][vehicle_type]
        
        # Корректировка ставки в зависимости от срока
        if params.months > 60:
            base_rate += 0.02
        elif params.months < 24:
            base_rate -= 0.01
            
        # Корректировка для лизинга с учетом выкупной стоимости
        if params.financing_type == 'leasing' and params.vehicle:
            residual_value = params.vehicle.get_residual_value(params.months)
            financed_amount = params.financed_amount - residual_value
        else:
            financed_amount = params.financed_amount
            residual_value = 0
        
        # Расчет платежа
        monthly_payment = self.calculate_annuity_payment(financed_amount, base_rate, params.months)
        
        # Добавляем страховку если включена
        if params.insurance_included:
            insurance_cost = params.amount * 0.005 / 12  # 0.5% годовых
            monthly_payment += insurance_cost
            
        if params.life_insurance:
            life_insurance_cost = 500  # фиксированная сумма
            monthly_payment += life_insurance_cost
        
        # Расчет итоговых значений
        total_payment = monthly_payment * params.months
        if params.financing_type == 'leasing':
            total_payment += residual_value
            
        overpayment = total_payment - params.financed_amount
        effective_rate = self.calculate_effective_rate(params, monthly_payment)
        
        # Генерация графика
        schedule = self.generate_schedule(params, monthly_payment, base_rate)
        
        # Формирование условий
        conditions = {
            'base_rate': round(base_rate * 100, 1),
            'vehicle_type': vehicle_type,
            'residual_value': round(residual_value, 2) if residual_value > 0 else None,
            'insurance_included': params.insurance_included,
            'life_insurance': params.life_insurance
        }
        
        return CalculationResult(
            monthly_payment=round(monthly_payment, 2),
            total_payment=round(total_payment, 2),
            overpayment=round(overpayment, 2),
            effective_rate=round(effective_rate, 2),
            schedule=schedule,
            approval_status="pending",
            approval_probability=0.0,
            conditions=conditions,
            calculation_id=self._generate_calculation_id()
        )
    
    def _generate_calculation_id(self) -> str:
        """Генерация уникального ID расчета"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"CALC_{timestamp}"

# ==================== СИСТЕМА ПРЕДОДОБРЕНИЯ ====================

class ScoringSystem(BaseScoringEngine):
    """Система скоринга для предварительного одобрения"""
    
    def __init__(self):
        self.rules = {
            'min_income_ratio': 0.4,  # Платеж не более 40% от дохода
            'min_age': 21,
            'max_age': 70,
            'min_experience': 3,  # месяцев на текущем месте
            'required_documents': ['passport', 'income_certificate']
        }
    
    def assess_client(self, client: ClientData, params: CalculationParameters) -> Tuple[float, str]:
        """Оценка клиента и расчет вероятности одобрения"""
        
        score = 100.0
        reasons = []
        
        # Проверка возраста
        birth_year = int(client.birth_date.split('.')[-1])
        current_year = datetime.now().year
        age = current_year - birth_year
        
        if age < self.rules['min_age']:
            score -= 30
            reasons.append(f"Возраст менее {self.rules['min_age']} лет")
        elif age > self.rules['max_age']:
            score -= 20
            reasons.append(f"Возраст более {self.rules['max_age']} лет")
        
        # Проверка дохода
        calculator = SmartCalculator()
        temp_result = calculator.calculate(params)
        
        payment_to_income_ratio = temp_result.monthly_payment / client.monthly_income
        
        if payment_to_income_ratio > self.rules['min_income_ratio']:
            reduction = (payment_to_income_ratio - self.rules['min_income_ratio']) * 100
            score -= reduction
            reasons.append(f"Высокое соотношение платеж/доход: {payment_to_income_ratio:.1%}")
        
        # Проверка стажа
        if client.experience_months < self.rules['min_experience']:
            score -= 15
            reasons.append(f"Маленький стаж на текущем месте: {client.experience_months} мес.")
        
        # Проверка типа занятости
        if client.employment_type == 'self_employed':
            score -= 10
            reasons.append("Самозанятый - повышенный риск")
        elif client.employment_type == 'business_owner':
            score -= 5
            reasons.append("Владелец бизнеса - средний риск")
        
        # Ограничение score в пределах 0-100
        score = max(0, min(100, score))
        
        # Определение статуса
        if score >= 70:
            status = "pre_approved"
        elif score >= 50:
            status = "conditional_approval"
        else:
            status = "rejected"
        
        return score, status

# ==================== КОНФИГУРАТОР ПРОДУКТОВ ====================

class ProductConfigurator:
    """Конфигуратор финансовых продуктов"""
    
    def __init__(self, config_file: str = 'products_config.json'):
        self.products = self._load_products(config_file)
    
    def _load_products(self, config_file: str) -> Dict:
        """Загрузка конфигурации продуктов из файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Конфигурация по умолчанию
            return {
                'credit_products': [
                    {
                        'id': 'credit_std',
                        'name': 'Стандартный кредит',
                        'min_amount': 100000,
                        'max_amount': 5000000,
                        'min_months': 12,
                        'max_months': 84,
                        'min_initial': 0.15,
                        'available_for': ['new', 'used']
                    },
                    {
                        'id': 'credit_premium',
                        'name': 'Премиум кредит',
                        'min_amount': 500000,
                        'max_amount': 10000000,
                        'min_months': 12,
                        'max_months': 60,
                        'min_initial': 0.20,
                        'available_for': ['new']
                    }
                ],
                'leasing_products': [
                    {
                        'id': 'leasing_std',
                        'name': 'Стандартный лизинг',
                        'min_amount': 300000,
                        'max_amount': 10000000,
                        'min_months': 12,
                        'max_months': 60,
                        'min_initial': 0.10,
                        'residual_percent': 0.20,
                        'available_for': ['new', 'used']
                    }
                ]
            }
    
    def get_available_products(self, vehicle: Vehicle, client_data: ClientData) -> List[Dict]:
        """Получение списка доступных продуктов для клиента и автомобиля"""
        available = []
        
        # Проверяем кредитные продукты
        for product in self.products.get('credit_products', []):
            if self._is_product_available(product, vehicle, client_data):
                product['type'] = 'credit'
                available.append(product)
        
        # Проверяем лизинговые продукты
        for product in self.products.get('leasing_products', []):
            if self._is_product_available(product, vehicle, client_data):
                product['type'] = 'leasing'
                available.append(product)
        
        return available
    
    def _is_product_available(self, product: Dict, vehicle: Vehicle, client_data: ClientData) -> bool:
        """Проверка доступности продукта"""
        
        # Проверка типа автомобиля
        if vehicle.category not in product.get('available_for', []):
            return False
        
        # Проверка суммы
        if vehicle.price < product.get('min_amount', 0):
            return False
        if vehicle.price > product.get('max_amount', float('inf')):
            return False
        
        # Проверка минимального первоначального взноса
        min_initial_amount = vehicle.price * product.get('min_initial', 0)
        
        return True

# ==================== ОСНОВНОЙ КЛАСС ПРИЛОЖЕНИЯ ====================

class SmartFinanceApp:
    """Основной класс приложения"""
    
    def __init__(self):
        self.calculator = SmartCalculator()
        self.scoring = ScoringSystem()
        self.configurator = ProductConfigurator()
        self.current_session = {}
    
    def start_new_session(self):
        """Начало новой сессии расчета"""
        self.current_session = {
            'session_id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'client_data': None,
            'vehicle': None,
            'parameters': None,
            'result': None
        }
    
    def input_vehicle_data(self) -> Vehicle:
        """Ввод данных об автомобиле"""
        print("\n" + "="*50)
        print("ВВОД ДАННЫХ ОБ АВТОМОБИЛЕ")
        print("="*50)
        
        brand = input("Марка автомобиля (например, Volkswagen): ")
        model = input("Модель (например, Tiguan): ")
        year = int(input("Год выпуска: "))
        price = float(input("Стоимость (руб.): "))
        vin = input("VIN-номер: ")
        category = input("Тип (new - новый, used - с пробегом): ")
        
        return Vehicle(
            brand=brand,
            model=model,
            year=year,
            price=price,
            vin=vin,
            category=category
        )
    
    def input_client_data(self) -> ClientData:
        """Ввод данных клиента"""
        print("\n" + "="*50)
        print("ВВОД ПЕРСОНАЛЬНЫХ ДАННЫХ")
        print("="*50)
        print("Все данные защищены и шифруются")
        
        full_name = input("ФИО (Иванов Иван Иванович): ")
        birth_date = input("Дата рождения (дд.мм.гггг): ")
        passport_series = input("Серия паспорта (4 цифры): ")
        passport_number = input("Номер паспорта (6 цифр): ")
        phone = input("Телефон (+7XXXXXXXXXX): ")
        email = input("Email: ")
        monthly_income = float(input("Ежемесячный доход (руб.): "))
        employment_type = input("Тип занятости (employed/self_employed/business_owner): ")
        experience_months = int(input("Стаж на текущем месте (мес.): "))
        
        client = ClientData(
            full_name=full_name,
            birth_date=birth_date,
            passport_series=passport_series,
            passport_number=passport_number,
            phone=phone,
            email=email,
            monthly_income=monthly_income,
            employment_type=employment_type,
            experience_months=experience_months
        )
        
        # Валидация
        is_valid, message = client.validate()
        if not is_valid:
            print(f"Ошибка: {message}")
            return self.input_client_data()
        
        return client
    
    def input_calculation_parameters(self, vehicle: Vehicle) -> CalculationParameters:
        """Ввод параметров расчета"""
        print("\n" + "="*50)
        print("ПАРАМЕТРЫ ФИНАНСИРОВАНИЯ")
        print("="*50)
        
        financing_type = input("Тип финансирования (credit/leasing): ")
        initial_payment = float(input(f"Первоначальный взнос (мин. {vehicle.price * 0.15:.0f} руб.): "))
        months = int(input("Срок (мес., от 12 до 84): "))
        
        insurance = input("Включить страховку КАСКО? (yes/no): ").lower() == 'yes'
        life_insurance = input("Включить страхование жизни? (yes/no): ").lower() == 'yes'
        
        return CalculationParameters(
            financing_type=financing_type,
            amount=vehicle.price,
            initial_payment=initial_payment,
            months=months,
            vehicle=vehicle,
            insurance_included=insurance,
            life_insurance=life_insurance
        )
    
    def run_scoring(self, client: ClientData, params: CalculationParameters) -> Tuple[float, str]:
        """Запуск скоринга для предодобрения"""
        print("\n" + "="*50)
        print("ПРОВЕРКА ПРЕДОДОБРЕНИЯ")
        print("="*50)
        
        score, status = self.scoring.assess_client(client, params)
        
        print(f"Скоринговый балл: {score:.1f}/100")
        print(f"Статус: {self._get_status_description(status)}")
        
        return score, status
    
    def _get_status_description(self, status: str) -> str:
        """Описание статуса одобрения"""
        descriptions = {
            'pre_approved': '✅ Предварительно одобрено',
            'conditional_approval': '⚠️  Одобрено с условиями',
            'rejected': '❌ Отклонено'
        }
        return descriptions.get(status, '⏳ На рассмотрении')
    
    def calculate_and_display(self, params: CalculationParameters, approval_status: str):
        """Расчет и отображение результатов"""
        print("\n" + "="*50)
        print("РЕЗУЛЬТАТЫ РАСЧЕТА")
        print("="*50)
        
        # Проверка параметров
        is_valid, message = self.calculator.validate_parameters(params)
        if not is_valid:
            print(f"Ошибка в параметрах: {message}")
            return
        
        # Расчет
        result = self.calculator.calculate(params)
        result.approval_status = approval_status
        
        # Отображение результатов
        print(f"\nЕжемесячный платеж: {result.monthly_payment:,.2f} руб.")
        print(f"Общая сумма выплат: {result.total_payment:,.2f} руб.")
        print(f"Переплата: {result.overpayment:,.2f} руб.")
        print(f"Эффективная ставка: {result.effective_rate:.2f}%")
        print(f"ID расчета: {result.calculation_id}")
        
        # Дополнительная информация
        if params.financing_type == 'leasing' and params.vehicle:
            residual = params.vehicle.get_residual_value(params.months)
            print(f"Выкупная стоимость: {residual:,.2f} руб.")
        
        # График платежей (первые 6 месяцев)
        print("\nГрафик платежей (первые 6 месяцев):")
        print("-"*60)
        print(f"{'Месяц':<10} {'Дата':<15} {'Платеж':<15} {'Остаток долга':<15}")
        print("-"*60)
        
        for payment in result.schedule[:6]:
            print(f"{payment['month']:<10} {payment['date']:<15} "
                  f"{payment['payment']:<15.2f} {payment['balance']:<15.2f}")
        
        if len(result.schedule) > 6:
            print(f"... и ещё {len(result.schedule) - 6} месяцев")
        
        # Сохранение в сессию
        self.current_session['result'] = result
        
        # Предложение сохранить
        self._offer_save_result(result)
    
    def _offer_save_result(self, result: CalculationResult):
        """Предложение сохранить результаты"""
        save = input("\nСохранить результаты расчета? (yes/no): ").lower()
        if save == 'yes':
            filename = f"calculation_{result.calculation_id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"Результаты сохранены в файл: {filename}")
    
    def get_recommendations(self, client: ClientData, vehicle: Vehicle) -> List[Dict]:
        """Получение рекомендаций по продуктам"""
        available_products = self.configurator.get_available_products(vehicle, client)
        
        print("\n" + "="*50)
        print("РЕКОМЕНДУЕМЫЕ ПРОДУКТЫ")
        print("="*50)
        
        recommendations = []
        for product in available_products:
            # Рассчитываем для каждого продукта
            params = CalculationParameters(
                financing_type=product['type'],
                amount=vehicle.price,
                initial_payment=vehicle.price * product.get('min_initial', 0.15),
                months=min(60, product.get('max_months', 60)),
                vehicle=vehicle
            )
            
            result = self.calculator.calculate(params)
            
            recommendation = {
                'product_name': product['name'],
                'type': product['type'],
                'monthly_payment': result.monthly_payment,
                'rate': result.conditions['base_rate'],
                'recommendation_reason': self._generate_recommendation_reason(client, product)
            }
            
            recommendations.append(recommendation)
            
            # Вывод рекомендации
            print(f"\n{product['name']} ({product['type']}):")
            print(f"  Ежемесячный платеж: {result.monthly_payment:,.2f} руб.")
            print(f"  Ставка: {result.conditions['base_rate']}%")
            print(f"  Рекомендация: {recommendation['recommendation_reason']}")
        
        return recommendations
    
    def _generate_recommendation_reason(self, client: ClientData, product: Dict) -> str:
        """Генерация причины рекомендации"""
        reasons = []
        
        if client.monthly_income > 100000 and product.get('min_initial', 0) >= 0.2:
            reasons.append("подходит для высокого дохода")
        
        if client.experience_months > 24 and product['type'] == 'credit':
            reasons.append("хорошая кредитная история")
        
        if client.employment_type == 'business_owner' and product['type'] == 'leasing':
            reasons.append("налоговые преимущества лизинга")
        
        return "; ".join(reasons) if reasons else "стандартное предложение"
    
    def run(self):
        """Основной метод запуска приложения"""
        print("="*60)
        print("УМНЫЙ КОНФИГУРАТОР И КАЛЬКУЛЯТОР КРЕДИТА/ЛИЗИНГА")
        print("Версия для ООО 'ГРВ' (бренд 'Евроальянс')")
        print("="*60)
        
        # Начало новой сессии
        self.start_new_session()
        
        # Ввод данных
        vehicle = self.input_vehicle_data()
        client = self.input_client_data()
        
        # Рекомендации продуктов
        self.get_recommendations(client, vehicle)
        
        # Ввод параметров расчета
        params = self.input_calculation_parameters(vehicle)
        
        # Проверка предодобрения
        score, approval_status = self.run_scoring(client, params)
        
        if approval_status == 'rejected':
            print("\nК сожалению, заявка не может быть одобрена.")
            print("Рекомендуем увеличить первоначальный взнос или выбрать другой автомобиль.")
            return
        
        # Расчет и вывод результатов
        self.calculate_and_display(params, approval_status)
        
        # Завершение
        print("\n" + "="*50)
        print("РАСЧЕТ ЗАВЕРШЕН")
        print("="*50)
        print(f"Сессия: {self.current_session['session_id']}")
        print("Спасибо за использование нашего сервиса!")
        print("Для оформления заявки обратитесь к менеджеру 'Евроальянс'.")
# database.py - модуль работы с БД
import asyncpg
from datetime import datetime
from typing import Optional, List
import json

class DatabaseManager:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn)
    
    async def save_client(self, client_data: dict) -> str:
        """Сохранение клиента с шифрованием критичных полей"""
        async with self.pool.acquire() as conn:
            # В реальности используем pgcrypto для шифрования
            client_id = await conn.fetchval("""
                INSERT INTO clients (
                    passport_hash, 
                    full_name_encrypted,
                    monthly_income,
                    employment_type,
                    experience_months
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, 
            client_data['passport_hash'],
            client_data['encrypted_name'],
            client_data['monthly_income'],
            client_data['employment_type'],
            client_data['experience_months'])
            
            return client_id
    
    async def save_calculation(self, calculation_data: dict) -> str:
        """Сохранение расчета"""
        async with self.pool.acquire() as conn:
            calc_id = await conn.fetchval("""
                INSERT INTO calculations (
                    client_id, vehicle_id, financing_type,
                    amount, initial_payment, months,
                    monthly_payment, total_payment, effective_rate,
                    approval_status, approval_score, session_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """, *calculation_data.values())
            
            return calc_id
    
    async def get_client_calculations(self, passport_hash: str) -> List[dict]:
        """Получение истории расчетов клиента"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT c.*, calc.created_at, calc.approval_status
                FROM clients c
                JOIN calculations calc ON c.id = calc.client_id
                WHERE c.passport_hash = $1
                ORDER BY calc.created_at DESC
                LIMIT 10
            """, passport_hash)
            
            return [dict(row) for row in rows]
    
    async def get_popular_products(self, days: int = 30) -> List[dict]:
        """Аналитика: популярные продукты"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    financing_type,
                    AVG(amount) as avg_amount,
                    AVG(months) as avg_months,
                    COUNT(*) as request_count,
                    SUM(CASE WHEN approval_status = 'pre_approved' THEN 1 ELSE 0 END) as approved_count
                FROM calculations
                WHERE created_at >= NOW() - INTERVAL '$1 days'
                GROUP BY financing_type
                ORDER BY request_count DESC
            """, days)
            
            return [dict(row) for row in rows]

# app_with_db.py - основной класс
class SmartFinanceAppWithDB:
    def __init__(self, db_manager: DatabaseManager):
        self.calculator = SmartCalculator()
        self.scoring = ScoringSystem()
        self.configurator = ProductConfigurator()
        self.db = db_manager
        self.current_user = None  # Текущий менеджер
    
    async def run_with_db(self):
        """Обновленный поток с сохранением в БД"""
        # ... предыдущие шаги ввода данных ...
        
        # После расчета сохраняем в БД
        client_id = await self.db.save_client({
            'passport_hash': client.get_hash(),
            'encrypted_name': self._encrypt_field(client.full_name),
            'monthly_income': client.monthly_income,
            'employment_type': client.employment_type,
            'experience_months': client.experience_months
        })
        
        calculation_id = await self.db.save_calculation({
            'client_id': client_id,
            'vehicle_id': await self._save_vehicle(vehicle),
            'financing_type': params.financing_type,
            'amount': params.amount,
            'initial_payment': params.initial_payment,
            'months': params.months,
            'monthly_payment': result.monthly_payment,
            'total_payment': result.total_payment,
            'effective_rate': result.effective_rate,
            'approval_status': approval_status,
            'approval_score': score,
            'session_data': json.dumps({
                'insurance_included': params.insurance_included,
                'life_insurance': params.life_insurance,
                'conditions': result.conditions
            })
        })
        
        # Сохранение сессии
        await self.db.save_session({
            'user_id': self.current_user,
            'client_id': client_id,
            'calculation_id': calculation_id
        })
        
        print(f"Расчет сохранен в базе. ID: {calculation_id}")

# ==================== ТОЧКА ВХОДА ====================

def main():
    """Точка входа в приложение"""
    app = SmartFinanceApp()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\nПроизошла ошибка: {str(e)}")
        print("Пожалуйста, свяжитесь с технической поддержкой")
    finally:
        print("\nДо свидания!")

if __name__ == "__main__":
    main()