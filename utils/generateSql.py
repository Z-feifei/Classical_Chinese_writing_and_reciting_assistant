import re
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://feifei123:4RQl2C3Bzam1WGr4@mysql5.sqlpub.com:3310/classical_chinese'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# 数据模型定义
class LexicalParticle(db.Model):
    __tablename__ = 'lexical_particles'
    id = db.Column(db.Integer, primary_key=True)
    character = db.Column(db.String(2), nullable=False, unique=True)
    parts_of_speech = db.relationship('PartOfSpeech', backref='particle', cascade='all, delete-orphan')


class PartOfSpeech(db.Model):
    __tablename__ = 'parts_of_speech'
    id = db.Column(db.Integer, primary_key=True)
    particle_id = db.Column(db.Integer, db.ForeignKey('lexical_particles.id'), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    sub_category = db.Column(db.String(5))
    definitions = db.relationship('Definition', backref='pos', cascade='all, delete-orphan')


class Definition(db.Model):
    __tablename__ = 'definitions'
    id = db.Column(db.Integer, primary_key=True)
    pos_id = db.Column(db.Integer, db.ForeignKey('parts_of_speech.id'), nullable=False)
    definition = db.Column(db.Text, nullable=False)
    examples = db.relationship('Example', backref='definition', cascade='all, delete-orphan')


class Example(db.Model):
    __tablename__ = 'examples'
    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey('definitions.id'), nullable=False)
    example = db.Column(db.Text, nullable=False)


def parse_document(content):
    lexicals = []
    # 分割实虚词章节
    sections = re.findall(r'### \d+\. (.+?)(?=###|\Z)', content, flags=re.DOTALL)

    for section in sections:
        lines = [line.strip() for line in section.split('\n') if line.strip()]
        if not lines:
            continue

        lexical = {'character': lines[0], 'parts_of_speech': []}
        current_category = None
        current_subcat = None

        for line in lines[1:]:
            # 匹配词性分类 (1) 连词
            if re.match(r'^（\d+）', line):
                current_category = re.sub(r'^（\d+）', '', line).strip()
                current_subcat = None
                continue

            # 匹配子分类 a.
            if match := re.match(r'^([a-z])\.', line):
                current_subcat = match.group(1)
                continue

            # 解析释义
            if line.startswith('释义：'):
                definition = line.split('：', 1)[1].strip()
                # 查找或创建对应的词性分类
                pos = next((p for p in lexical['parts_of_speech']
                            if p['category'] == current_category and p['sub_category'] == current_subcat), None)
                if not pos:
                    pos = {'category': current_category, 'sub_category': current_subcat, 'definitions': []}
                    lexical['parts_of_speech'].append(pos)
                pos['definitions'].append({'definition': definition, 'examples': []})

            # 解析例句
            elif line.startswith('例句：'):
                examples = re.split(r'①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩', line.split('：', 1)[1])
                examples = [ex.strip() for ex in examples if ex.strip()]
                if lexical['parts_of_speech'] and lexical['parts_of_speech'][-1]['definitions']:
                    lexical['parts_of_speech'][-1]['definitions'][-1]['examples'] = examples

        lexicals.append(lexical)
    return lexicals


def insert_data(lexicals):
    with app.app_context():
        for lex in lexicals:
            # 插入实虚词
            particle = LexicalParticle.query.filter_by(character=lex['character']).first()
            if not particle:
                particle = LexicalParticle(character=lex['character'])
                db.session.add(particle)
                db.session.commit()

            # 插入词性分类
            for pos in lex['parts_of_speech']:
                pos_entry = PartOfSpeech(
                    particle_id=particle.id,
                    category=pos['category'],
                    sub_category=pos.get('sub_category')
                )
                db.session.add(pos_entry)
                db.session.commit()

                # 插入释义
                for defn in pos['definitions']:
                    def_entry = Definition(
                        pos_id=pos_entry.id,
                        definition=defn['definition']
                    )
                    db.session.add(def_entry)
                    db.session.commit()

                    # 插入例句
                    for ex in defn.get('examples', []):
                        ex_entry = Example(
                            definition_id=def_entry.id,
                            example=ex
                        )
                        db.session.add(ex_entry)
                    db.session.commit()

print("尝试打开文档！")
with open('document.txt', 'r', encoding='utf-8') as f:
    print("打开文档成功！")
    content = f.read()
    print("读取文档成功！")

# 解析文档生成JSON
lexicals = parse_document(content)
print("数据解析完成！")
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(lexicals, f, ensure_ascii=False, indent=2)

# 插入数据库
insert_data(lexicals)
print("数据插入完成！")

if __name__ == '__main__':
    app.run(debug=False)
