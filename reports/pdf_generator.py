"""Генератор PDF отчетов"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from matrix_calculator.models import MatrixData, MatrixResult
from PIL import Image as PILImage
import io


class PDFGenerator:
    """Генератор PDF отчетов"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Настройка стилей"""
        # Заголовок
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Подзаголовок
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Обычный текст
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2C3E50'),
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
    
    def generate_pdf(self, data: MatrixData, result: MatrixResult) -> bytes:
        """Генерирует PDF отчет"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Заголовок
        title = Paragraph("ЛИЧНАЯ МАТРИЦА СУДЬБЫ", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 10*mm))
        
        # Информация о клиенте
        client_info = f"""
        <b>Имя:</b> {data.name}<br/>
        <b>Дата рождения:</b> {data.birth_date.strftime('%d.%m.%Y')}<br/>
        """
        if data.gender:
            gender_text = "Мужской" if data.gender == "male" else "Женский"
            client_info += f"<b>Пол:</b> {gender_text}<br/>"
        
        story.append(Paragraph(client_info, self.styles['CustomBody']))
        story.append(Spacer(1, 10*mm))
        
        # Основные числа
        story.append(Paragraph("ОСНОВНЫЕ ЧИСЛА", self.styles['CustomHeading']))
        
        numbers_data = [
            ['Параметр', 'Значение'],
            ['День рождения', str(result.day)],
            ['Месяц рождения', str(result.month)],
            ['Год рождения', f"{result.year} ({result.year_reduced})"],
            ['Личное число', str(result.personal_number)],
            ['Число судьбы', str(result.destiny_number)],
            ['Число души', str(result.soul_number)],
            ['Число личности', str(result.personality_number)],
            ['Путь жизни', str(result.life_path)],
            ['Выражение', str(result.expression)],
        ]
        
        numbers_table = Table(numbers_data, colWidths=[100*mm, 90*mm])
        numbers_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECF0F1')])
        ]))
        
        story.append(numbers_table)
        story.append(Spacer(1, 10*mm))
        
        # Матрица
        story.append(Paragraph("МАТРИЦА СУДЬБЫ", self.styles['CustomHeading']))
        
        matrix_data = [
            [
                str(result.matrix['top_left']),
                str(result.matrix['top_center']),
                str(result.matrix['top_right'])
            ],
            [
                str(result.matrix['middle_left']),
                str(result.matrix['center']),
                str(result.matrix['middle_right'])
            ],
            [
                str(result.matrix['bottom_left']),
                str(result.matrix['bottom_center']),
                str(result.matrix['bottom_right'])
            ]
        ]
        
        matrix_table = Table(matrix_data, colWidths=[60*mm, 60*mm, 60*mm])
        matrix_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 20),
            ('GRID', (0, 0), (-1, -1), 2, colors.black),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#F39C12')),  # Центр
            ('TEXTCOLOR', (1, 1), (1, 1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        story.append(matrix_table)
        story.append(Spacer(1, 10*mm))
        
        # Кармические числа
        if result.karmic_numbers:
            story.append(Paragraph("КАРМИЧЕСКИЕ ЧИСЛА", self.styles['CustomHeading']))
            karmic_text = f"Обнаружены кармические числа: {', '.join(map(str, result.karmic_numbers))}"
            story.append(Paragraph(karmic_text, self.styles['CustomBody']))
            story.append(Spacer(1, 10*mm))
        
        # Интерпретации
        story.append(Paragraph("ИНТЕРПРЕТАЦИИ", self.styles['CustomHeading']))
        
        interpretations_map = {
            'personal_number': 'Личное число',
            'destiny_number': 'Число судьбы',
            'soul_number': 'Число души',
            'personality_number': 'Число личности',
            'life_path': 'Путь жизни',
            'expression': 'Выражение',
        }
        
        for key, title in interpretations_map.items():
            if key in result.interpretations and result.interpretations[key]:
                story.append(Paragraph(f"<b>{title}</b>", self.styles['CustomBody']))
                interpretation = result.interpretations[key].strip()
                # Очищаем от лишних переносов строк
                interpretation = ' '.join(interpretation.split())
                story.append(Paragraph(interpretation, self.styles['CustomBody']))
                story.append(Spacer(1, 5*mm))
        
        # Футер
        story.append(Spacer(1, 20*mm))
        footer = Paragraph(
            f"<i>Отчет сгенерирован автоматически<br/>"
            f"Дата создания: {result.model_dump().get('created_at', 'N/A')}</i>",
            self.styles['Normal']
        )
        story.append(footer)
        
        # Собираем PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


def generate_pdf_report(data: MatrixData, result: MatrixResult) -> bytes:
    """Удобная функция для генерации PDF"""
    generator = PDFGenerator()
    return generator.generate_pdf(data, result)
