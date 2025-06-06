from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import generate_password_hash

app = Flask(__name__)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)


# 用户系统数据模型
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(255), default='')
    personal_tag = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    study_records = db.relationship('StudyRecord', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')


# 用户背诵进度模型
class RecitationProgress(db.Model):
    __tablename__ = 'recitation_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    last_studied = db.Column(db.DateTime, default=datetime.utcnow)
    mastery_level = db.Column(db.Integer, default=0)  # 0-陌生, 1-熟悉, 2-掌握
    wrong_count = db.Column(db.Integer, default=0)
    right_count = db.Column(db.Integer, default=0)

    # 关系
    user = db.relationship('User', backref=db.backref('progress', lazy=True, cascade='all, delete-orphan'))
    particle = db.relationship('LexicalParticle')


# 用户背词记录模型
class VocabularyRecord(db.Model):
    __tablename__ = 'vocabulary_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    study_time = db.Column(db.DateTime, default=datetime.utcnow)
    wrong_example_ids = db.Column(db.JSON)  # 存储答错的例句ID
    correct_answer_ids = db.Column(db.JSON)  # 存储正确答案的释义ID
    user_answers = db.Column(db.JSON)  # 存储用户选择的答案

    # 关系
    particle = db.relationship('LexicalParticle')


# 用户收藏题目模型
class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # 文章内容
    question = db.Column(db.Text)  # 题目
    answer = db.Column(db.Text)    # 答案
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 实词库数据模型
class LexicalParticle(db.Model):
    __tablename__ = 'lexical_particles'

    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(50), nullable=False, unique=True)  # 汉字

    # 建立一对多关系
    parts_of_speech = db.relationship('PartOfSpeech', backref='particle', cascade='all, delete-orphan')


class PartOfSpeech(db.Model):
    __tablename__ = 'parts_of_speech'

    id = db.Column(db.Integer, primary_key=True)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 词性分类
    sub_category = db.Column(db.String(5))  # 子分类标记

    # 建立一对多关系
    definitions = db.relationship('Definition', backref='pos', cascade='all, delete-orphan')


class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('parts_of_speech.id'), nullable=False)
    definition = db.Column(db.Text, nullable=False)  # 详细释义

    # 建立一对多关系
    examples = db.relationship('Example', backref='definition', cascade='all, delete-orphan')


class Example(db.Model):
    __tablename__ = 'examples'

    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey('definitions.id'), nullable=False)
    example = db.Column(db.Text, nullable=False)  # 文言例句



def init_database():
    """初始化数据库"""
    with app.app_context():
        try:
            # 第一步：清除现有数据表
            print("正在清除现有数据表...")
            db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
            db.session.commit()

            # 按模型依赖顺序逐个删除
            meta = db.metadata
            for table in reversed(meta.sorted_tables):
                try:
                    db.session.execute(text(f'DROP TABLE IF EXISTS `{table.name}`'))
                    print(f"已删除数据表：{table.name}")
                except Exception as e:
                    print(f"删除表 {table.name} 时出错：{e}")

            db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1'))
            db.session.commit()

            # 第二步：创建所有数据表
            print("正在创建数据表...")
            db.create_all()
            print("数据表创建完成")

            # 第三步：创建默认管理员用户
            print("正在创建默认管理员用户...")
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                personal_tag='系统管理员'
            )

            db.session.add(admin_user)
            db.session.commit()
            print("默认管理员用户创建完成 (用户名: admin, 密码: admin123)")

            print("数据库初始化完成！")

        except Exception as e:
            db.session.rollback()
            print(f"数据库初始化失败：{str(e)}")
            raise


def create_sample_data():
    """创建示例数据"""
    with app.app_context():
        try:
            # 创建测试用户
            test_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('test123'),
                personal_tag='测试用户'
            )
            db.session.add(test_user)
            db.session.commit()

            # 为测试用户创建学习记录
            sample_record = StudyRecord(
                user_id=test_user.id,
                article_content='子曰："学而时习之，不亦说乎？有朋自远方来，不亦乐乎？人不知而不愠，不亦君子乎？"',
                score=85
            )
            db.session.add(sample_record)

            # 为测试用户创建收藏
            sample_favorite = Favorite(
                user_id=test_user.id,
                title='论语·学而',
                content='子曰："学而时习之，不亦说乎？有朋自远方来，不亦乐乎？人不知而不愠，不亦君子乎？"',
                question='孔子认为"君子"应具备怎样的品格？请结合原文具体分析',
                answer='孔子将"不愠"作为君子的基本标准，强调道德自律和精神独立性，区别于功利性的人际交往'
            )
            db.session.add(sample_favorite)

            db.session.commit()
            print("示例数据创建完成")

        except Exception as e:
            db.session.rollback()
            print(f"示例数据创建失败：{str(e)}")


if __name__ == '__main__':
    print("正在执行主程序...")
    # 初始化数据库
    init_database()

    # 创建示例数据（可选）
    create_sample_data()

    print("\n数据库设置完成！")
    print("默认管理员账号：")
    print("用户名: admin")
    print("密码: admin123")
    print("\n测试用户账号：")
    print("用户名: testuser")
    print("密码: test123")