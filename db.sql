CREATE TABLE
  `arxiv_papers` (
    `paper_id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '论文唯一标识符',
    `title` varchar(512) COLLATE utf8mb4_general_ci NOT NULL COMMENT '论文英文标题',
    `chinese_title` text COLLATE utf8mb4_general_ci COMMENT '论文中文标题',
    `publish_date` date NOT NULL COMMENT '论文发布日期',
    `pdf_link` text COLLATE utf8mb4_general_ci COMMENT '论文PDF链接',
    `web_link` text COLLATE utf8mb4_general_ci COMMENT '论文网页链接',
    `categories` text COLLATE utf8mb4_general_ci COMMENT '论文分类信息',
    `research_direction` text COLLATE utf8mb4_general_ci COMMENT '研究方向',
    `main_content` text COLLATE utf8mb4_general_ci COMMENT '论文主要内容和贡献',
    `has_chinese_author` tinyint (1) DEFAULT '0' COMMENT '是否有中国作者',
    `has_chinese_email` tinyint (1) DEFAULT '0' COMMENT '是否有中国作者邮箱',
    `processed_date` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
    PRIMARY KEY (`paper_id`)
  ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = 'arXiv论文信息表';

CREATE TABLE
  `paper_authors` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT '作者ID',
    `paper_id` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '论文ID',
    `author_name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '作者姓名',
    `position` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '作者位置（第一作者、通讯作者等）',
    `affiliation` text COLLATE utf8mb4_general_ci COMMENT '所属机构',
    `email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '电子邮箱',
    `country` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '国家',
    `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `paper_author` (`paper_id`, `author_name`),
    CONSTRAINT `paper_authors_ibfk_1` FOREIGN KEY (`paper_id`) REFERENCES `arxiv_papers` (`paper_id`) ON DELETE CASCADE
  ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '论文作者信息表';

CREATE TABLE `chinese_universities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name_cn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '中文名',
  `name_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '英文名',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '官网',
  `city` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '城市',
  `is_985` tinyint(1) DEFAULT '0' COMMENT '是否985',
  `is_211` tinyint(1) DEFAULT '0' COMMENT '是否211',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_cn` (`name_cn`)
) ENGINE=InnoDB AUTO_INCREMENT=125 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大学表';

CREATE TABLE `universities_college` (
  `id` int NOT NULL AUTO_INCREMENT,
  `university_id` int NOT NULL COMMENT 'chinese_universities id',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '学院名',
  `website` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '学院官网',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_col` (`university_id`,`name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=125 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='大学院系表';


CREATE TABLE
  `universities_teacher` (
    `id` int NOT NULL AUTO_INCREMENT COMMENT 'ID',
    `university_id` int NOT NULL COMMENT 'chinese_universities id',
    `college_id` int NOT NULL COMMENT 'universities_college id',
    `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '教师姓名',
    `sex` int DEFAULT '0' COMMENT '性别, 0: 未知, 1: 男, 2: 女',
    `email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '电子邮箱',
    `is_national_fun` tinyint(1) DEFAULT '0' COMMENT '是否主持过国家基金项目',
    `is_cs` tinyint(1) DEFAULT '0' COMMENT '教师是否与计算机相关',
    `bookname` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '著作名',
    `title` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '职称',
    `job_title` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '职位',
    `tel` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '电话',
    `homepage` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '个人主页',
    `research_direction` text COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '研究方向',
    `papers` text COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '论文',
    `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `collage_teacher` (`college_id`, `name`, `email`)
  ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '大学教师表';