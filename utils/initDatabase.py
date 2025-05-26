from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)


# 实虚词表模型
class LexicalParticle(db.Model):
    __tablename__ = 'lexical_particles'

    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(50), nullable=False, unique=True)  # 汉字

    # 建立一对多关系
    parts_of_speech = db.relationship('PartOfSpeech', backref='particle', cascade='all, delete-orphan')


# 词性分类表模型
class PartOfSpeech(db.Model):
    __tablename__ = 'parts_of_speech'

    id = db.Column(db.Integer, primary_key=True)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 词性分类
    sub_category = db.Column(db.String(5))  # 子分类标记

    # 建立一对多关系
    definitions = db.relationship('Definition', backref='pos', cascade='all, delete-orphan')


# 释义表模型
class Definition(db.Model):
    __tablename__ = 'definitions'

    id = db.Column(db.Integer, primary_key=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('parts_of_speech.id'), nullable=False)
    definition = db.Column(db.Text, nullable=False)  # 详细释义


    # 建立一对多关系
    examples = db.relationship('Example', backref='definition', cascade='all, delete-orphan')


# 例句表模型
class Example(db.Model):
    __tablename__ = 'examples'

    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey('definitions.id'), nullable=False)
    example = db.Column(db.Text, nullable=False)  # 文言例句


with app.app_context():
    try:
        # 第一步：清除现有数据表
        db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
        db.session.commit()

        # 按模型依赖顺序逐个删除
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(text(f'DROP TABLE IF EXISTS `{table.name}`'))
            print(f"已删除数据表：{table.name}")

        db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1'))
        db.session.commit()

        # 第二步：创建所有数据表
        db.create_all()
        print("数据表创建完成")

    except Exception as e:
        db.session.rollback()
        print(f"操作失败：{str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=False)