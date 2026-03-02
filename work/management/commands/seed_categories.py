from django.core.management.base import BaseCommand
from work.models import Category


class Command(BaseCommand):
    help = 'Seed the database with initial help request categories'

    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Programming & CS',
                'slug': 'programming',
                'icon': 'fas fa-code',
                'color': '#6C63FF',
                'description': 'Help with coding, algorithms, data structures, and computer science concepts.',
            },
            {
                'name': 'Mathematics',
                'slug': 'mathematics',
                'icon': 'fas fa-calculator',
                'color': '#06d6a0',
                'description': 'Help with calculus, algebra, statistics, and other math topics.',
            },
            {
                'name': 'Science & Engineering',
                'slug': 'science-engineering',
                'icon': 'fas fa-flask',
                'color': '#f59e0b',
                'description': 'Physics, chemistry, electrical, mechanical, and other engineering subjects.',
            },
            {
                'name': 'Writing & Research',
                'slug': 'writing-research',
                'icon': 'fas fa-pen-fancy',
                'color': '#ec4899',
                'description': 'Essay writing, research papers, thesis support, and academic writing.',
            },
            {
                'name': 'Design & Creative',
                'slug': 'design-creative',
                'icon': 'fas fa-palette',
                'color': '#8b5cf6',
                'description': 'Graphic design, UI/UX, presentations, and creative projects.',
            },
            {
                'name': 'Languages',
                'slug': 'languages',
                'icon': 'fas fa-language',
                'color': '#3b82f6',
                'description': 'Language learning, translation, and communication skills.',
            },
            {
                'name': 'Career & Internships',
                'slug': 'career-internships',
                'icon': 'fas fa-briefcase',
                'color': '#14b8a6',
                'description': 'Resume review, interview prep, internship advice, and career guidance.',
            },
            {
                'name': 'Other',
                'slug': 'other',
                'icon': 'fas fa-ellipsis-h',
                'color': '#6b7280',
                'description': 'Anything else you need help with.',
            },
        ]

        created_count = 0
        existing_count = 0

        for cat_data in categories:
            obj, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data,
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded {created_count} categories ({existing_count} already existed)'
            )
        )
