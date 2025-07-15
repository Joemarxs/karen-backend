from rest_framework import serializers
from .models import Product, Category

class ProductFrontendSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'long_description', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    # Read: nested category object
    category_detail = CategorySerializer(source='category', read_only=True)
    # Write: accept category by ID
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'unit',
            'category',        # for write
            'category_detail', # for read
            'image',
        ]
